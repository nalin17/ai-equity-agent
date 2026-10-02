"""Market data adapters (architecture 40A item 7, 40B step 6, 40G.2).

An adapter turns one provider's file format into the canonical price record
used by the trust chain. It is the ONLY place that knows a provider's column
names, date format or scope rule, so swapping or adding a provider changes
this module and nothing downstream (40A item 7).

An adapter translates; it never repairs. A value it cannot translate (for
example an unreadable date) is passed on unchanged, and the trust chain
quarantines the row. The raw file is what gets stored and hashed.

Acquisition (how the file got onto disk) is separate from methodology
(40G.2): files are downloaded by hand from nseindia.com into data/inbox.
A provider format change shows up here as a loud error, never as a
loosened check further down.
"""
import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from data_quality.trust_chain import CANONICAL_COLUMNS, NoDataError, ingest_records
from core.database import now_utc


class AdapterError(Exception):
    """The file cannot be read, or its format is not one we recognise."""


@dataclass(frozen=True)
class Provider:
    name: str
    version: str
    source_id: str
    required_columns: tuple
    scope_column: str
    scope_values: frozenset
    mapping: dict          # canonical column -> provider column
    date_format: str       # strptime format of the provider's date column; "" means already YYYY-MM-DD
    excluded_isin_prefixes: frozenset = frozenset()  # instrument classes declared out of scope
    name_column: str = ""  # the provider's security-name column, if it has one (used only for 6D evidence)

    @property
    def scope_rule(self):
        rule = f"{self.scope_column} in {sorted(self.scope_values)}"
        if self.excluded_isin_prefixes:
            rule += f" and ISIN not starting with {sorted(self.excluded_isin_prefixes)}"
        return rule

    def in_scope(self, row):
        if (row.get(self.scope_column) or "").strip() not in self.scope_values:
            return False
        isin = (row.get(self.mapping["isin"]) or "").strip()
        return not any(isin.startswith(p) for p in self.excluded_isin_prefixes)

    def to_canonical(self, row):
        rec = {c: (row.get(self.mapping[c]) or "").strip() for c in CANONICAL_COLUMNS}
        if self.date_format and rec["trade_date"]:
            try:
                rec["trade_date"] = datetime.strptime(rec["trade_date"], self.date_format).date().isoformat()
            except ValueError:
                pass  # left as received; the trust chain quarantines it
        return rec


# ADR-003: equity research covers company shares only. ISINs starting with INF
# are mutual-fund units and ETFs: they trade in the EQ series but are not companies.
NOT_COMPANY_SHARES = frozenset({"INF"})

# NSE capital-market bhavcopy, the format used until July 2024.
NSE_CM_LEGACY = Provider(
    name="nse_cm_bhavcopy_legacy",
    version="2",
    source_id="nse_bhavcopy_equity",
    required_columns=("SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY", "TIMESTAMP", "ISIN"),
    scope_column="SERIES",
    scope_values=frozenset({"EQ"}),
    mapping={"symbol": "SYMBOL", "isin": "ISIN", "trade_date": "TIMESTAMP", "open": "OPEN",
             "high": "HIGH", "low": "LOW", "close": "CLOSE", "volume": "TOTTRDQTY"},
    date_format="%d-%b-%Y",
    excluded_isin_prefixes=NOT_COMPANY_SHARES,
)

# NSE capital-market bhavcopy in the UDiFF format, used from July 2024.
NSE_CM_UDIFF = Provider(
    name="nse_cm_bhavcopy_udiff",
    version="2",
    source_id="nse_bhavcopy_equity",
    required_columns=("TradDt", "ISIN", "TckrSymb", "SctySrs", "OpnPric", "HghPric", "LwPric",
                      "ClsPric", "TtlTradgVol"),
    scope_column="SctySrs",
    scope_values=frozenset({"EQ"}),
    mapping={"symbol": "TckrSymb", "isin": "ISIN", "trade_date": "TradDt", "open": "OpnPric",
             "high": "HghPric", "low": "LwPric", "close": "ClsPric", "volume": "TtlTradgVol"},
    date_format="",
    excluded_isin_prefixes=NOT_COMPANY_SHARES,
    name_column="FinInstrmNm",
)

PROVIDERS = (NSE_CM_LEGACY, NSE_CM_UDIFF)


def read_raw_table(path):
    """Read a .csv, or a .zip holding exactly one .csv. Returns (header, [(row_number, row)])."""
    path = Path(path)
    data = path.read_bytes()
    if path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                members = [n for n in z.namelist() if n.lower().endswith(".csv")]
                if len(members) != 1:
                    raise AdapterError(f"{path.name}: expected exactly one .csv inside the zip, found {members}")
                data = z.read(members[0])
        except zipfile.BadZipFile:
            raise AdapterError(f"{path.name}: not a valid zip file") from None
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AdapterError(f"{path.name}: not UTF-8 text") from None
    reader = csv.reader(io.StringIO(text))
    try:
        header = [h.strip() for h in next(reader)]
    except StopIteration:
        raise NoDataError(f"{path.name}: empty file - nothing is stored") from None
    rows = []
    for row_number, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        rows.append((row_number, {h: v for h, v in zip(header, values) if h}))
    return header, rows


def detect_provider(header, providers=PROVIDERS):
    """Exactly one provider must recognise the header, otherwise stop."""
    columns = set(header)
    matches = [p for p in providers if set(p.required_columns) <= columns]
    if len(matches) != 1:
        found = ", ".join(h for h in header if h) or "(none)"
        raise AdapterError(
            f"Unrecognised file format ({len(matches)} providers match). Columns found: {found}. "
            "If NSE changed its format, the adapter must be updated - checks are never loosened (40G.2)."
        )
    return matches[0]


def provider_named(name, providers=PROVIDERS):
    matches = [p for p in providers if p.name == name]
    if len(matches) != 1:
        raise AdapterError(f"Unknown provider {name!r}")
    return matches[0]


def run_rows(conn, run_id):
    """Re-read the stored raw file of an ingestion run with the provider it used.

    Returns (provider, [(row_number, raw_row, canonical_row, security_name)]) for
    in-scope rows. Used as identity evidence (6D) and for retries - never for prices.
    """
    found = conn.execute(
        "SELECT a.stored_path, r.artifact_id FROM ingestion_runs r JOIN raw_artifacts a"
        " ON a.artifact_id = r.artifact_id WHERE r.run_id = ?", [run_id]).fetchone()
    if found is None:
        raise AdapterError(f"Unknown ingestion run {run_id}")
    provider_name = conn.execute(
        "SELECT provider FROM adapter_runs WHERE run_id = ? UNION SELECT provider FROM retry_runs"
        " WHERE run_id = ?", [run_id, run_id]).fetchone()
    if provider_name is None:
        raise AdapterError(f"Run {run_id} was not read by a market adapter")
    provider = provider_named(provider_name[0])
    _, rows = read_raw_table(found[0])
    out = []
    for row_number, row in rows:
        if provider.in_scope(row):
            name = (row.get(provider.name_column) or "").strip() if provider.name_column else ""
            out.append((row_number, row, provider.to_canonical(row), name))
    return provider, out


def retry_quarantined(conn, artifact_id, reason, only_isins=None):
    """Run quarantined rows of an already-stored raw file through the trust chain again.

    Used after reference data has grown (for example an identity bridge). Only
    rows for only_isins are retried when it is given, so rows that still cannot
    pass are not quarantined twice. Rows already trusted are not touched;
    earlier quarantine records stay as history.
    """
    if not reason or not reason.strip():
        raise AdapterError("A retry must state its reason")
    artifact = conn.execute(
        "SELECT source_id, stored_path, retrieved_at, published_at, publication_evidence FROM raw_artifacts"
        " WHERE artifact_id = ?", [artifact_id]).fetchone()
    if artifact is None:
        raise AdapterError(f"Unknown raw artifact {artifact_id}")
    source_id, stored_path, retrieved_at, published_at, evidence = artifact
    runs = [r[0] for r in conn.execute("SELECT run_id FROM ingestion_runs WHERE artifact_id = ?", [artifact_id])]
    if not runs:
        raise AdapterError(f"Artifact {artifact_id} was never ingested as prices")
    marks = ", ".join("?" * len(runs))
    quarantined = {r[0] for r in conn.execute(f"SELECT row_number FROM quarantine WHERE run_id IN ({marks})", runs)}
    trusted = {r[0] for r in conn.execute(f"SELECT row_number FROM price_provenance WHERE run_id IN ({marks})", runs)}
    provider, rows = run_rows(conn, runs[0])
    records = [(n, raw, canonical) for n, raw, canonical, _ in rows if n in quarantined - trusted
               and (only_isins is None or canonical["isin"] in only_isins)]
    if not records:
        return {"artifact_id": artifact_id, "rows_retried": 0}

    def on_run(c, run_id):
        c.execute("INSERT INTO retry_runs VALUES (?, ?, ?, ?, ?, ?)",
                  [run_id, artifact_id, provider.name, len(records), reason.strip(), now_utc()])

    report = ingest_records(conn, source_id, stored_path, records, retrieved_at, published_at, evidence,
                            on_run=on_run, existing_artifact_id=artifact_id)
    report.update(rows_retried=len(records))
    return report


def ingest_market_file(conn, path, retrieved_at, published_at=None, publication_evidence=None,
                       raw_dir=None, providers=PROVIDERS):
    """Detect the provider, map in-scope rows to canonical records, run the trust chain."""
    header, rows = read_raw_table(path)
    provider = detect_provider(header, providers)
    records, out_of_scope = [], 0
    for row_number, row in rows:
        if not provider.in_scope(row):
            out_of_scope += 1
            continue
        records.append((row_number, row, provider.to_canonical(row)))
    if not records:
        raise NoDataError(f"{Path(path).name}: no rows in scope ({provider.scope_rule}) - nothing is stored")

    def on_run(c, run_id):
        c.execute(
            "INSERT INTO adapter_runs VALUES (?, ?, ?, ?, ?, ?, ?)",
            [run_id, provider.name, provider.version, len(rows), out_of_scope, provider.scope_rule, now_utc()],
        )

    report = ingest_records(conn, provider.source_id, path, records, retrieved_at,
                            published_at, publication_evidence, raw_dir, on_run=on_run)
    report.update(provider=provider.name, rows_in_file=len(rows), rows_out_of_scope=out_of_scope)
    return report
