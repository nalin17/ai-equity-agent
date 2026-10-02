"""Load NSE's list of listed securities (EQUITY_L.csv) into the entity registry.

This list is a CURRENT SNAPSHOT (source timestamp_semantics: snapshot_no_vintage).
It says what each company is called and which symbol it trades under today,
not what it was called in the past. So:

- A new ISIN becomes an entity, with its symbol valid from its listing date
  and a dated 'listing' event.
- An ISIN already known is never overwritten. If the name or symbol in the
  file differs from the registry, the row is rejected and recorded: a rename
  or symbol change is a dated event (Stage 3), not something a snapshot can
  tell us the date of.
- A symbol already used by a different ISIN is rejected for the same reason.
- Every rejected row is kept exactly as received with its reason.

Historical symbol changes are therefore NOT loaded by this module. Price rows
that use an old symbol are quarantined by the trust chain until the change
is recorded - fail closed, never guessed.
"""
import json
from datetime import datetime

from core.database import now_utc, run_in_transaction
from ingestion.market_adapters import AdapterError, read_raw_table
from ingestion.source_registry import get_source
from data_quality.trust_chain import NoDataError
from provenance.raw_store import store_raw_artifact
from universe.entities import EntityError, add_alias, add_entity, record_event, validate_isin

SOURCE_ID = "nse_equity_list"
REQUIRED_COLUMNS = ("SYMBOL", "NAME OF COMPANY", "SERIES", "DATE OF LISTING", "ISIN NUMBER")
LISTING_DATE_FORMAT = "%d-%b-%Y"  # e.g. 06-OCT-2008


class RowRejected(Exception):
    pass


def _load_row(conn, row):
    symbol = (row.get("SYMBOL") or "").strip()
    name = (row.get("NAME OF COMPANY") or "").strip()
    isin = (row.get("ISIN NUMBER") or "").strip()
    listed = (row.get("DATE OF LISTING") or "").strip()
    if not symbol or not name:
        raise RowRejected("symbol and company name are required")
    try:
        validate_isin(isin)
    except EntityError as e:
        raise RowRejected(str(e)) from None
    try:
        listed_on = datetime.strptime(listed, LISTING_DATE_FORMAT).date().isoformat()
    except ValueError:
        raise RowRejected(f"DATE OF LISTING is not DD-MON-YYYY: {listed!r}") from None

    known = conn.execute("SELECT legal_name FROM entities WHERE isin = ?", [isin]).fetchone()
    if known:
        if known[0] != name:
            raise RowRejected(
                f"name differs from the registry ({known[0]!r}); a rename is a dated event, never an overwrite"
            )
        open_symbols = [r[0] for r in conn.execute(
            "SELECT alias_value FROM entity_aliases WHERE isin = ? AND alias_type = 'nse_symbol'"
            " AND valid_to IS NULL", [isin])]
        if open_symbols == [symbol]:
            return "already_present"
        raise RowRejected(
            f"symbol differs from the registry ({open_symbols}); record the symbol change with its date"
        )

    owner = conn.execute(
        "SELECT isin FROM entity_aliases WHERE alias_type = 'nse_symbol' AND alias_value = ?"
        " AND valid_to IS NULL", [symbol]).fetchone()
    if owner:
        raise RowRejected(f"symbol {symbol!r} already belongs to {owner[0]}; reuse needs a dated event")
    try:
        add_entity(conn, isin, name)
        add_alias(conn, isin, "nse_symbol", symbol, listed_on)
        record_event(conn, isin, "listing", listed_on, f"listed on NSE as {symbol} (from {SOURCE_ID})")
    except EntityError as e:
        raise RowRejected(str(e)) from None
    return "added"


def load_equity_list(conn, path, retrieved_at, raw_dir=None):
    """Load one downloaded EQUITY_L file. Returns a report dict."""
    get_source(conn, SOURCE_ID)
    header, rows = read_raw_table(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise AdapterError(f"Not an NSE equity list: missing columns {missing}")
    if not rows:
        raise NoDataError("The equity list has no rows - nothing is stored")

    def work(c):
        artifact_id, _ = store_raw_artifact(c, SOURCE_ID, path, retrieved_at, raw_dir=raw_dir)
        counts = {"added": 0, "already_present": 0}
        rejections = []
        for row_number, row in rows:
            c.execute("SAVEPOINT equity_row")  # a rejected row leaves nothing half-written
            try:
                counts[_load_row(c, row)] += 1
            except RowRejected as r:
                c.execute("ROLLBACK TO equity_row")
                rejections.append((row_number, str(r), json.dumps(row, sort_keys=True)))
            c.execute("RELEASE equity_row")
        load_id = c.execute(
            "INSERT INTO entity_list_loads (artifact_id, rows_in_file, entities_added, already_present,"
            " rejected, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
            [artifact_id, len(rows), counts["added"], counts["already_present"], len(rejections), now_utc()],
        ).lastrowid
        c.executemany("INSERT INTO entity_list_rejections VALUES (?, ?, ?, ?)",
                      [(load_id, n, reason, raw) for n, reason, raw in rejections])
        return {
            "load_id": load_id,
            "rows_in_file": len(rows),
            "entities_added": counts["added"],
            "already_present": counts["already_present"],
            "rejected": len(rejections),
            "first_rejections": [(n, reason) for n, reason, _ in rejections[:5]],
        }

    return run_in_transaction(conn, work)
