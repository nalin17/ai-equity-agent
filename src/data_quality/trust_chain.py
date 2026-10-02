"""The Data Trust chain for daily prices (architecture Section 4, 40B step 3).

Trust is produced by an ORDERED pipeline. Each stage may quarantine a record;
no stage may repair one. A quarantined record is kept exactly as received,
with the stage and the reason it failed.

Input is a CSV in the canonical price format below. Converting a real
exchange file into this format is the job of a market data adapter (a later
stage), so a provider change never reaches this module.

Stages implemented here, in the architecture's order:
  1. schema_and_type             every field present and of the right type
  2. timestamp_and_availability  dates valid and not after the file was obtained
  3. entity_resolution           ISIN known on that date; symbol agrees with ISIN
  4. deduplication               repeated rows collapse; contradictory rows quarantine
  5. cross_source_consistency    agrees with an already-trusted value, never overwrites it
  6. anomaly_detection           impossible prices and volumes
Provenance (raw file hash + row number) is recorded for every trusted fact.

Stages NOT implemented yet (declared in the Stage 4 acceptance record):
corporate action and version check, implausible period-to-period changes,
point-in-time versioning of corrections, survivorship / universe control.
"""
import csv
import io
import json
import re
from enum import StrEnum
from pathlib import Path

from core.database import now_utc, run_in_transaction
from core.dates import strict_iso_date
from ingestion.source_registry import get_source
from provenance.availability import parse_timestamp
from provenance.raw_store import store_raw_artifact
from universe.entities import EntityError, InvalidIsinError, resolve, validate_isin

PIPELINE_VERSION = "price-trust-chain-1"
CANONICAL_COLUMNS = ("symbol", "isin", "trade_date", "open", "high", "low", "close", "volume")
PRICE_FIELDS = ("open", "high", "low", "close")

PLAIN_DECIMAL = re.compile(r"^\d+(\.\d+)?$")
PLAIN_INTEGER = re.compile(r"^\d+$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TrustStage(StrEnum):
    """The stages, in the order they run."""
    SCHEMA_AND_TYPE = "schema_and_type"
    TIMESTAMP_AND_AVAILABILITY = "timestamp_and_availability"
    ENTITY_RESOLUTION = "entity_resolution"
    DEDUPLICATION = "deduplication"
    CROSS_SOURCE_CONSISTENCY = "cross_source_consistency"
    ANOMALY_DETECTION = "anomaly_detection"


class TrustChainError(Exception):
    """The whole file is unusable (wrong columns, unregistered source)."""


class NoDataError(TrustChainError):
    """The file has no data rows. Architecture 4C.1: an empty result is never
    stored as if it were data - it is raised, so the caller knows nothing arrived."""


class RecordRejected(Exception):
    def __init__(self, stage, reason):
        super().__init__(reason)
        self.stage = stage
        self.reason = reason


# ---- the individual stages ------------------------------------------------

def check_schema_and_type(row):
    """Stage 1. Returns a typed record or raises RecordRejected."""
    stage = TrustStage.SCHEMA_AND_TYPE
    empty = [c for c in CANONICAL_COLUMNS if not (row.get(c) or "").strip()]
    if empty:
        raise RecordRejected(stage, f"empty fields: {empty}")
    rec = {c: row[c].strip() for c in CANONICAL_COLUMNS}
    try:
        validate_isin(rec["isin"])
    except InvalidIsinError as e:
        raise RecordRejected(stage, str(e)) from None
    if not ISO_DATE.match(rec["trade_date"]):
        raise RecordRejected(stage, f"trade_date must be YYYY-MM-DD, got {rec['trade_date']!r}")
    try:
        strict_iso_date(rec["trade_date"])
    except ValueError:
        raise RecordRejected(stage, f"trade_date is not a real date: {rec['trade_date']!r}") from None
    for field in PRICE_FIELDS:
        if not PLAIN_DECIMAL.match(rec[field]):
            raise RecordRejected(stage, f"{field} is not a plain number: {rec[field]!r}")
        rec[field] = float(rec[field])
    if not PLAIN_INTEGER.match(rec["volume"]):
        raise RecordRejected(stage, f"volume is not a whole number: {rec['volume']!r}")
    rec["volume"] = int(rec["volume"])
    return rec


def check_timestamp(rec, retrieved_at, published_at=None):
    """Stage 2. A trade cannot be dated after the file that reports it existed."""
    stage = TrustStage.TIMESTAMP_AND_AVAILABILITY
    trade_date = strict_iso_date(rec["trade_date"])
    if trade_date > retrieved_at.date():
        raise RecordRejected(stage, f"trade_date {trade_date} is after the file was retrieved ({retrieved_at})")
    if published_at is not None and trade_date > published_at.date():
        raise RecordRejected(stage, f"trade_date {trade_date} is after the file was published ({published_at})")


def check_entity(conn, rec):
    """Stage 3. The ISIN must be known on the trade date, and the symbol must
    mean that same ISIN on that date. Nothing is guessed."""
    stage = TrustStage.ENTITY_RESOLUTION
    try:
        resolve(conn, rec["isin"], rec["trade_date"])
        symbol_isin = resolve(conn, rec["symbol"], rec["trade_date"], alias_type="nse_symbol")
    except EntityError as e:
        raise RecordRejected(stage, str(e)) from None
    if symbol_isin != rec["isin"]:
        raise RecordRejected(
            stage,
            f"symbol {rec['symbol']!r} meant {symbol_isin} on {rec['trade_date']}, but the row says {rec['isin']}",
        )


def price_values(rec):
    return tuple(rec[f] for f in PRICE_FIELDS) + (rec["volume"],)


def check_anomalies(rec):
    """Stage 6. Values that cannot be true. Detected, never corrected."""
    stage = TrustStage.ANOMALY_DETECTION
    o, h, l, c = (rec[f] for f in PRICE_FIELDS)
    if min(o, h, l, c) <= 0:
        raise RecordRejected(stage, "a price is zero or negative")
    if l > h:
        raise RecordRejected(stage, f"low {l} is above high {h}")
    if not (l <= o <= h and l <= c <= h):
        raise RecordRejected(stage, f"open {o} or close {c} is outside the low-high range {l}-{h}")


# ---- the pipeline ---------------------------------------------------------

def read_price_file(file_path):
    text = Path(file_path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in CANONICAL_COLUMNS if c not in header]
    if missing:
        raise TrustChainError(f"{file_path}: missing columns {missing}; expected {list(CANONICAL_COLUMNS)}")
    reader.fieldnames = header
    rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    if not rows:
        raise NoDataError(f"{file_path}: no data rows - nothing is stored")
    return rows


def ingest_price_file(conn, source_id, file_path, retrieved_at,
                      published_at=None, publication_evidence=None, raw_dir=None):
    """Run a canonical price file through the trust chain. Returns a report dict.

    Everything happens in one transaction: either the whole file is recorded
    (trusted rows, quarantined rows, provenance) or nothing is.
    """
    get_source(conn, source_id)  # unregistered sources are refused
    retrieved = parse_timestamp(retrieved_at)
    published = parse_timestamp(published_at) if published_at is not None else None
    rows = read_price_file(file_path)  # raises before anything is stored

    def work(c):
        artifact_id, sha = store_raw_artifact(c, source_id, file_path, retrieved_at,
                                              published_at, publication_evidence, raw_dir)
        run_id = c.execute(
            "INSERT INTO ingestion_runs (artifact_id, pipeline_version, rows_total, rows_trusted,"
            " rows_duplicate, rows_quarantined, recorded_at) VALUES (?, ?, ?, 0, 0, 0, ?)",
            [artifact_id, PIPELINE_VERSION, len(rows), now_utc()],
        ).lastrowid
        counts = {"trusted": 0, "duplicate": 0, "quarantined": 0}
        by_stage = {}

        def quarantine(row_number, row, stage, reason):
            c.execute(
                "INSERT INTO quarantine (run_id, row_number, failed_stage, reason, raw_record, recorded_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [run_id, row_number, str(stage), reason, json.dumps(row, sort_keys=True), now_utc()],
            )
            counts["quarantined"] += 1
            by_stage[str(stage)] = by_stage.get(str(stage), 0) + 1

        # Stages 1-3, row by row. Row numbers count the header as line 1.
        passed = []
        for row_number, row in enumerate(rows, start=2):
            try:
                rec = check_schema_and_type(row)
                check_timestamp(rec, retrieved, published)
                check_entity(c, rec)
            except RecordRejected as r:
                quarantine(row_number, row, r.stage, r.reason)
                continue
            passed.append((row_number, row, rec))

        # Stage 4: group rows for the same security and day.
        groups = {}
        for item in passed:
            groups.setdefault((item[2]["isin"], item[2]["trade_date"]), []).append(item)

        for (isin, trade_date), items in groups.items():
            if len({price_values(rec) for _, _, rec in items}) > 1:
                for row_number, row, _ in items:
                    quarantine(row_number, row, TrustStage.DEDUPLICATION,
                               f"{len(items)} rows for {isin} on {trade_date} disagree with each other")
                continue
            rec = items[0][2]
            try:
                # Stage 5: compare with what is already trusted. Never overwrite.
                existing = c.execute(
                    "SELECT price_id, open_price, high_price, low_price, close_price, volume"
                    " FROM trusted_prices WHERE isin = ? AND trade_date = ?",
                    [isin, trade_date],
                ).fetchone()
                if existing and tuple(existing[1:]) != price_values(rec):
                    raise RecordRejected(
                        TrustStage.CROSS_SOURCE_CONSISTENCY,
                        f"already trusted as {tuple(existing[1:])}, this file says {price_values(rec)};"
                        " conflicts are never averaged or overwritten",
                    )
                # Stage 6: impossible values.
                check_anomalies(rec)
            except RecordRejected as r:
                for row_number, row, _ in items:
                    quarantine(row_number, row, r.stage, r.reason)
                continue

            if existing:
                price_id = existing[0]
                counts["duplicate"] += len(items)
            else:
                price_id = c.execute(
                    "INSERT INTO trusted_prices (isin, trade_date, open_price, high_price, low_price,"
                    " close_price, volume, first_run_id, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [isin, trade_date, rec["open"], rec["high"], rec["low"], rec["close"],
                     rec["volume"], run_id, now_utc()],
                ).lastrowid
                counts["trusted"] += 1
                counts["duplicate"] += len(items) - 1
            for row_number, _, _ in items:
                c.execute("INSERT INTO price_provenance VALUES (?, ?, ?)", [price_id, run_id, row_number])

        c.execute(
            "UPDATE ingestion_runs SET rows_trusted = ?, rows_duplicate = ?, rows_quarantined = ?"
            " WHERE run_id = ?",
            [counts["trusted"], counts["duplicate"], counts["quarantined"], run_id],
        )
        return {
            "run_id": run_id,
            "artifact_id": artifact_id,
            "sha256": sha,
            "rows_total": len(rows),
            "rows_trusted": counts["trusted"],
            "rows_duplicate": counts["duplicate"],
            "rows_quarantined": counts["quarantined"],
            "quarantined_by_stage": by_stage,
        }

    return run_in_transaction(conn, work)
