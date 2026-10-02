"""Raw and corporate-action-adjusted daily price series (architecture 6C, 6C.1, 6D, 40A item 13).

Raw exchange prices are immutable: raw_series() returns them exactly as trusted,
for one ISIN. With follow_bridges=True it also shows the rows of an older ISIN
connected by an identity bridge (6D), each row still labelled with its own ISIN.

The adjusted series is DERIVED. It is computed on request, never stored over
the raw prices, and carries its own identity: basis, policy version, the
actions applied, the bridges followed and the window it was built for.

Back-adjustment: every price dated BEFORE a factor action's ex-date is
multiplied by shares_before / shares_after, so the whole window is expressed
on the share basis in force at the window's end. Volumes scale the other way.

Fail closed (6C.1, 6D):
  - an action the policy does not support inside the window blocks it;
  - a split or bonus inside the window with NO prices before its ex-date
    (for example an ISIN change without a bridge) blocks it - the window is
    never silently shortened.
Blocking applies to that security and window only.

No factor is ever inferred from prices (criterion 64): factors come only from
recorded share ratios in corporate_actions.
"""
from dataclasses import dataclass

from core.dates import strict_iso_date
from ingestion.corporate_actions import POLICY_VERSION


class SeriesError(Exception):
    """The request itself is invalid, or the stored rows contradict each other."""


class AdjustmentBlocked(Exception):
    """The adjusted series for this security and window fails closed (6C.1, 6D)."""


@dataclass(frozen=True)
class PriceSeries:
    isin: str
    basis: str                 # "raw" or "adjusted"
    window_start: str
    window_end: str
    policy_version: str | None
    actions_applied: tuple     # action_ids of the factors used
    rows: tuple                # (trade_date, open, high, low, close, volume)
    row_isins: tuple = ()      # the ISIN each row was trusted under
    bridges_used: tuple = ()   # bridge_ids followed

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


def _rows_with_bridges(conn, isin, start, end):
    """Rows of this ISIN plus, for each bridge whose ex-date is in the window,
    the old ISIN's rows before that ex-date. Returns ([(row, isin)], bridge_ids)."""
    rows = [(r, isin) for r in _raw_rows(conn, isin, start, end)]
    used = []
    for bridge_id, old_isin, ex_date in conn.execute(
            "SELECT bridge_id, old_isin, ex_date FROM identity_bridges WHERE new_isin = ?"
            " AND ex_date > ? AND ex_date <= ? ORDER BY ex_date", [isin, start, end]).fetchall():
        rows += [(r, old_isin) for r in _raw_rows(conn, old_isin, start, end) if r[0] < ex_date]
        used.append(bridge_id)
    rows.sort(key=lambda item: item[0][0])
    dates = [r[0] for r, _ in rows]
    if len(dates) != len(set(dates)):
        raise SeriesError(f"{isin}: two ISINs have prices on the same date in {start} to {end}")
    return rows, tuple(used)


def raw_series(conn, isin, start, end, follow_bridges=False):
    """Prices exactly as trusted. Always available, whatever corporate actions exist."""
    _check_window(start, end)
    if follow_bridges:
        rows, used = _rows_with_bridges(conn, isin, start, end)
    else:
        rows, used = [(r, isin) for r in _raw_rows(conn, isin, start, end)], ()
    return PriceSeries(isin, "raw", start, end, None, (), tuple(r for r, _ in rows),
                       tuple(i for _, i in rows), used)


def adjusted_series(conn, isin, start, end):
    """Back-adjusted prices for one security and window, or AdjustmentBlocked."""
    _check_window(start, end)
    rows, used = _rows_with_bridges(conn, isin, start, end)
    isins = sorted({isin} | {i for _, i in rows})
    marks = ", ".join("?" * len(isins))
    blocked = conn.execute(
        f"SELECT action_id, action_type, ex_date FROM corporate_actions WHERE isin IN ({marks})"
        " AND treatment = 'blocked' AND ex_date > ? AND ex_date <= ? ORDER BY ex_date",
        [*isins, start, end],
    ).fetchall()
    if blocked:
        action_id, action_type, ex_date = blocked[0]
        raise AdjustmentBlocked(
            f"{isin}: '{action_type}' on {ex_date} (action {action_id}) is not supported by "
            f"{POLICY_VERSION}; the window {start} to {end} fails closed for this security only (6C.1)"
        )
    factors = conn.execute(
        "SELECT action_id, action_type, ex_date, shares_before, shares_after FROM corporate_actions WHERE isin = ?"
        " AND treatment = 'factor' AND ex_date > ? AND ex_date <= ? ORDER BY ex_date",
        [isin, start, end],
    ).fetchall()
    for action_id, action_type, ex_date, _, _ in factors:
        if not any(r[0] < ex_date for r, _ in rows):
            raise AdjustmentBlocked(
                f"{isin}: no prices before the {action_type} on {ex_date} (action {action_id}). If the ISIN "
                f"changed at that event, an identity bridge is needed (6D); the window {start} to {end} "
                "fails closed rather than being shortened"
            )
    adjusted = []
    for (trade_date, o, h, l, c, v), _ in rows:
        price_factor, volume_factor = 1.0, 1.0
        for _, _, ex_date, before, after in factors:
            if trade_date < ex_date:
                price_factor *= before / after
                volume_factor *= after / before
        adjusted.append((trade_date, o * price_factor, h * price_factor, l * price_factor, c * price_factor,
                         v * volume_factor))
    return PriceSeries(isin, "adjusted", start, end, POLICY_VERSION, tuple(f[0] for f in factors),
                       tuple(adjusted), tuple(i for _, i in rows), used)
