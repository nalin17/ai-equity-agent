"""Raw and corporate-action-adjusted daily price series (architecture 6C, 6C.1, 40A item 13).

Raw exchange prices are immutable: raw_series() returns them exactly as trusted.
The adjusted series is DERIVED. It is computed on request, never stored over
the raw prices, and carries its own identity: basis, policy version, the
actions applied and the window it was built for.

Back-adjustment: every price dated BEFORE a factor action's ex-date is
multiplied by shares_before / shares_after, so the whole window is expressed
on the share basis in force at the window's end. Volumes scale the other way.

Fail closed (6C.1): if an action the policy does not support has
window_start < ex_date <= window_end, the adjusted series for THAT security
and window is refused. Other securities and other windows are unaffected.

No factor is ever inferred from prices (criterion 64): factors come only from
recorded share ratios in corporate_actions.
"""
from dataclasses import dataclass

from core.dates import strict_iso_date
from ingestion.corporate_actions import POLICY_VERSION


class SeriesError(Exception):
    """The request itself is invalid."""


class AdjustmentBlocked(Exception):
    """An unsupported corporate action falls inside the requested window (6C.1)."""


@dataclass(frozen=True)
class PriceSeries:
    isin: str
    basis: str                 # "raw" or "adjusted"
    window_start: str
    window_end: str
    policy_version: str | None
    actions_applied: tuple     # action_ids of the factors used
    rows: tuple                # (trade_date, open, high, low, close, volume)

    def closes(self):
        return [r[4] for r in self.rows]


def _check_window(start, end):
    for name, value in (("start", start), ("end", end)):
        try:
            strict_iso_date(value)
        except ValueError:
            raise SeriesError(f"{name} must be YYYY-MM-DD, got {value!r}") from None
    if end < start:
        raise SeriesError("end must not be before start")


def _raw_rows(conn, isin, start, end):
    return conn.execute(
        "SELECT trade_date, open_price, high_price, low_price, close_price, volume FROM trusted_prices"
        " WHERE isin = ? AND trade_date >= ? AND trade_date <= ? ORDER BY trade_date",
        [isin, start, end],
    ).fetchall()


def raw_series(conn, isin, start, end):
    """Prices exactly as trusted. Always available, whatever corporate actions exist."""
    _check_window(start, end)
    return PriceSeries(isin, "raw", start, end, None, (), tuple(_raw_rows(conn, isin, start, end)))


def adjusted_series(conn, isin, start, end):
    """Back-adjusted prices for one security and window, or AdjustmentBlocked."""
    _check_window(start, end)
    blocked = conn.execute(
        "SELECT action_id, action_type, ex_date FROM corporate_actions WHERE isin = ? AND treatment = 'blocked'"
        " AND ex_date > ? AND ex_date <= ? ORDER BY ex_date",
        [isin, start, end],
    ).fetchall()
    if blocked:
        action_id, action_type, ex_date = blocked[0]
        raise AdjustmentBlocked(
            f"{isin}: '{action_type}' on {ex_date} (action {action_id}) is not supported by "
            f"{POLICY_VERSION}; the window {start} to {end} fails closed for this security only (6C.1)"
        )
    factors = conn.execute(
        "SELECT action_id, ex_date, shares_before, shares_after FROM corporate_actions WHERE isin = ?"
        " AND treatment = 'factor' AND ex_date > ? AND ex_date <= ? ORDER BY ex_date",
        [isin, start, end],
    ).fetchall()
    rows = []
    for trade_date, o, h, l, c, v in _raw_rows(conn, isin, start, end):
        price_factor, volume_factor = 1.0, 1.0
        for _, ex_date, before, after in factors:
            if trade_date < ex_date:
                price_factor *= before / after
                volume_factor *= after / before
        rows.append((trade_date, o * price_factor, h * price_factor, l * price_factor, c * price_factor,
                     v * volume_factor))
    return PriceSeries(isin, "adjusted", start, end, POLICY_VERSION, tuple(f[0] for f in factors), tuple(rows))
