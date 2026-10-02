"""Identity bridges - ISIN is not permanently stable (architecture 6D).

In India a face-value split usually gives the security a NEW ISIN. The prices
before the ex-date carry the old ISIN, the prices after it the new one. A
bridge connects the two for ONE corporate-action event, and only when ALL of
these are shown from the stored NSE files:

  1. a recorded split or bonus for the symbol on that ex-date
  2. exact symbol match on both sides
  3. the expected source series (the adapter's scope rule, e.g. EQ)
  4. exactly one ISIN for that symbol on the ex-date, and exactly one on the
     last day before it
  5. company-name continuity in the provider's own security-name column

Never allowed: symbol-only bridges, global ISIN equivalence, rewriting raw
identities. Each side keeps its own ISIN; the old ISIN becomes its own entity
with a dated isin_change event (Stage 3). Without full evidence no bridge is
made, and an adjusted series across that ex-date fails closed.

Prices are read here only as identity evidence (which ISIN traded under which
symbol on which day) - never to derive an adjustment factor.
"""
import json

from core.database import now_utc, run_in_transaction
from core.dates import strict_iso_date
from ingestion.market_adapters import provider_named, run_rows
from ingestion.nse_corporate_actions import normalise_name
from universe.entities import EntityError, add_entity, record_isin_change, resolve, validate_isin

BRIDGE_VERSION = "identity-bridge-1"


class BridgeRefused(Exception):
    """The evidence required by 6D is not all there. Nothing was written."""


def _provider_of_run(conn, run_id):
    row = conn.execute("SELECT provider FROM adapter_runs WHERE run_id = ? UNION"
                       " SELECT provider FROM retry_runs WHERE run_id = ?", [run_id, run_id]).fetchone()
    return provider_named(row[0]) if row else None


def create_bridge(conn, symbol, ex_date):
    """Bridge the ISIN change at one split/bonus, or raise BridgeRefused. Returns a report dict."""
    try:
        strict_iso_date(ex_date)
        new_isin = resolve(conn, symbol, ex_date, alias_type="nse_symbol")
    except (ValueError, EntityError) as e:
        raise BridgeRefused(f"{symbol} on {ex_date}: {e}") from None

    action = conn.execute(
        "SELECT action_id, action_type FROM corporate_actions WHERE isin = ? AND ex_date = ? AND treatment = 'factor'",
        [new_isin, ex_date]).fetchone()
    if action is None:
        raise BridgeRefused(f"{symbol}: no split or bonus recorded on {ex_date}; bridges exist only for such events")
    action_id, action_type = action
    if conn.execute("SELECT 1 FROM identity_bridges WHERE action_id = ?", [action_id]).fetchone():
        raise BridgeRefused(f"{symbol}: the {action_type} on {ex_date} is already bridged")
    if conn.execute("SELECT 1 FROM trusted_prices WHERE isin = ? AND trade_date < ?", [new_isin, ex_date]).fetchone():
        raise BridgeRefused(f"{symbol}: {new_isin} already has prices before {ex_date}; there is no ISIN change to bridge")

    # New side: the ex-date row, read back from the stored NSE file.
    new_run = conn.execute("SELECT first_run_id FROM trusted_prices WHERE isin = ? AND trade_date = ?",
                           [new_isin, ex_date]).fetchone()
    if new_run is None:
        raise BridgeRefused(f"{symbol}: no trusted price on the ex-date {ex_date}")
    new_provider, rows = run_rows(conn, new_run[0])
    new_side = [r for r in rows if r[2]["symbol"] == symbol and r[2]["trade_date"] == ex_date]
    if {r[2]["isin"] for r in new_side} != {new_isin} or len(new_side) != 1:
        raise BridgeRefused(f"{symbol}: the ex-date file does not show exactly one ISIN ({new_isin}) for the symbol")

    # Old side: the latest quarantined row for this symbol before the ex-date.
    candidates = []
    for run_id, raw in conn.execute("SELECT run_id, raw_record FROM quarantine"):
        provider = _provider_of_run(conn, run_id)
        if provider is None:
            continue
        rec = provider.to_canonical(json.loads(raw))
        if rec["symbol"] == symbol and rec["trade_date"] < ex_date and rec["isin"] != new_isin:
            candidates.append((rec["trade_date"], run_id))
    if not candidates:
        raise BridgeRefused(f"{symbol}: no quarantined rows under another ISIN before {ex_date}")
    last_old_date, old_run = max(candidates)
    old_provider, rows = run_rows(conn, old_run)
    old_side = [r for r in rows if r[2]["symbol"] == symbol and r[2]["trade_date"] == last_old_date]
    old_isins = {r[2]["isin"] for r in old_side}
    if len(old_side) != 1 or len(old_isins) != 1:
        raise BridgeRefused(f"{symbol}: {last_old_date} does not show exactly one ISIN for the symbol")
    old_isin = old_isins.pop()
    try:
        validate_isin(old_isin)
    except EntityError as e:
        raise BridgeRefused(f"{symbol}: {e}") from None

    # Name continuity, from the provider's own security-name column.
    if not (old_provider.name_column and new_provider.name_column):
        raise BridgeRefused(f"{symbol}: the file format has no security-name column; continuity cannot be shown")
    old_name, new_name = old_side[0][3], new_side[0][3]
    if not old_name or normalise_name(old_name) != normalise_name(new_name):
        raise BridgeRefused(f"{symbol}: names differ ({old_name!r} vs {new_name!r}); continuity not shown")

    legal_name = conn.execute("SELECT legal_name FROM entities WHERE isin = ?", [new_isin]).fetchone()[0]
    known_old = conn.execute("SELECT legal_name FROM entities WHERE isin = ?", [old_isin]).fetchone()
    if known_old and normalise_name(known_old[0]) != normalise_name(legal_name):
        raise BridgeRefused(f"{symbol}: {old_isin} is already registered as {known_old[0]!r}")
    evidence = (f"{action_type} on {ex_date}; NSE files: run {old_run} shows {symbol} as {old_isin} "
                f"({old_name}) on {last_old_date}, run {new_run[0]} shows {symbol} as {new_isin} ({new_name}) "
                f"on {ex_date}; {BRIDGE_VERSION}")

    def work(c):
        if not known_old:
            add_entity(c, old_isin, legal_name)
        record_isin_change(c, old_isin, new_isin, ex_date, evidence)
        return c.execute(
            "INSERT INTO identity_bridges (action_id, symbol, old_isin, new_isin, last_old_date, ex_date,"
            " old_evidence_run, new_evidence_run, evidence, bridge_version, recorded_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [action_id, symbol, old_isin, new_isin, last_old_date, ex_date, old_run, new_run[0],
             evidence, BRIDGE_VERSION, now_utc()],
        ).lastrowid

    bridge_id = run_in_transaction(conn, work)
    return {"bridge_id": bridge_id, "symbol": symbol, "old_isin": old_isin, "new_isin": new_isin,
            "last_old_date": last_old_date, "ex_date": ex_date, "action": action_type}


def bridge_candidates(conn):
    """(symbol, ex_date) of every recorded split/bonus that has no bridge yet."""
    return conn.execute(
        "SELECT a.alias_value, ca.ex_date FROM corporate_actions ca JOIN entity_aliases a"
        " ON a.isin = ca.isin AND a.alias_type = 'nse_symbol' AND a.valid_from <= ca.ex_date"
        " AND (a.valid_to IS NULL OR ca.ex_date < a.valid_to)"
        " WHERE ca.treatment = 'factor' AND ca.action_id NOT IN (SELECT action_id FROM identity_bridges)"
        " ORDER BY ca.ex_date").fetchall()
