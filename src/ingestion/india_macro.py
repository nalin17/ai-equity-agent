"""India macro context from MoSPI's eSankhyiki API (architecture 40B step 9a, 3G, 4C.1, 4G, 5A.1, 5B; ADR-009).

Input: answers of MoSPI's public data API (https://api.mospi.gov.in) - consumer prices (CPI), industrial
production (IIP) and quarterly national accounts (GDP) - fetched by the news fetcher, the only module
allowed to use the network. MoSPI's own datasets are Category A under the Government Statistics Data
Dissemination policy 2026: reuse is allowed with prominent attribution. Source - Ministry of Statistics and
Programme Implementation (MoSPI), National Statistics Office, eSankhyiki.

Rules, each found on MoSPI's real answers (03/04-Oct-2026):
  - Series are declared by a person in config/india_macro_series.yaml and recorded once, never silently
    changed. Each names the exact filters sent and the fields every returned row must carry.
  - Every page is kept byte for byte before it is used. An answer that is not MoSPI's paged list, reports
    failure, is empty, or whose pages do not add up to the stated total is refused whole - never 'no data'
    (4C.1). A row without the expected fields means the filter was not applied: the answer is refused
    whole (4G rule 7). MoSPI returns breakdown rows with the aggregate - asking for manufacturing also
    returns each of its 23 sub-industries - so the declared 'select' fields pick the aggregate row; the
    others are not stored.
  - MoSPI gives no publication time and, for these tables, no provisional or final mark (the GDP table's
    'revision' field is empty). A value is known from this system's first read of it: current decisions
    only, and historical replay stays in AVAILABILITY_REVIEW (5A.1, 5B.2). A value that changes in a later
    read is a new vintage; the old one stays.
  - A base-year change is a break: each base is its own series, never spliced. A back series recalculated
    on a newer base (CPI 2013-2024 on base 2024) is 'reconstructed': it shows the past as known today and
    never stands in for what was known at the time.
  - A blank measure is a value MoSPI does not publish - year-on-year inflation is blank for the first
    year of each base, as there is no earlier value on that base. It is counted, never stored or filled.
  - Periods: a month is dated by its first day; a GDP quarter is a financial-year quarter - Q1 of 2026-27
    is April-June 2026, dated 2026-04-01.
  - Nothing here is a covered security, a target or a benchmark, and a level is never a buy or sell signal
    on its own (3G rules 2-3).
"""
import json
import re
from pathlib import Path

import yaml

from core.config import PROJECT_ROOT
from core.database import now_utc, run_in_transaction
from data_quality.trust_chain import NoDataError
from ingestion.macro_context import GROUPS
from ingestion.market_adapters import AdapterError
from ingestion.source_registry import get_source
from provenance.availability import Availability, PitClaim, disposition, parse_timestamp
from provenance.raw_store import ArtifactError, sha256_bytes, store_raw_artifact

SOURCE_ID = "mospi_esankhyiki"
ATTRIBUTION = ("Source: Ministry of Statistics and Programme Implementation (MoSPI), National Statistics Office"
               " - eSankhyiki")
SERIES_FILE = PROJECT_ROOT / "config" / "india_macro_series.yaml"
API_PATHS = {"cpi": "/api/cpi/getCPIData", "iip": "/api/iip/getIipData", "nas": "/api/nas/getNASData"}
DATASETS = {"cpi": ("monthly", ("index", "inflation")), "iip": ("monthly", ("index", "growth_rate")),
            "nas": ("quarterly", ("constant_price", "current_price"))}
ENTRY_KEYS = {"series_id", "title", "group", "dataset", "request", "expect", "select", "measure", "unit", "status",
              "publisher", "licence"}
STATUSES = ("published", "reconstructed")
COLUMNS = ("series_id", "title", "factor_group", "dataset", "request", "expect", "row_select", "measure", "unit",
           "frequency", "status", "publisher", "licence")
PAGE_SIZE = 100
MAX_PAGES = 20
SERIES_ID = re.compile(r"^IN_[A-Z0-9_]{2,40}$")
VALUE = re.compile(r"^-?\d+(\.\d+)?$")
MONTHS = {name: number for number, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
     "December"), 1)}
FINANCIAL_YEAR = re.compile(r"^(\d{4})-(\d{2})$")
QUARTER_START = {"Q1": (0, 4), "Q2": (0, 7), "Q3": (0, 10), "Q4": (1, 1)}   # (year after the first, month)
META_KEYS = ("page", "totalRecords", "totalPages", "recordPerPage")
MISSING = object()
PROBLEMS_SHOWN = 10


class IndiaSeriesError(Exception):
    """config/india_macro_series.yaml is invalid or disagrees with what is recorded."""


class MospiResponseError(AdapterError):
    """A MoSPI answer cannot be used as a whole. Nothing is stored."""


class RowRefused(ValueError):
    """One row cannot be used; it is recorded as a problem."""


def canonical(mapping):
    return json.dumps(mapping, sort_keys=True, separators=(",", ":"))


# ---- the series registry ----------------------------------------------------------------

def load_series_file(path=SERIES_FILE):
    with open(Path(path), encoding="utf-8-sig") as f:
        data = yaml.safe_load(f) or {}
    return data.get("series") or []


def check_entry(entry):
    """One declared series as stored, or IndiaSeriesError."""
    if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
        keys = set(entry) if isinstance(entry, dict) else set()
        raise IndiaSeriesError(f"{entry.get('series_id') if keys else entry!r}: missing fields"
                               f" {sorted(ENTRY_KEYS - keys)}, unknown fields {sorted(keys - ENTRY_KEYS)}")
    sid = entry["series_id"]
    if not isinstance(sid, str) or not SERIES_ID.match(sid):
        raise IndiaSeriesError(f"{sid!r} is not a series id like IN_CPI24_GEN_INDEX")
    for field in ("title", "unit", "publisher", "licence"):
        if not isinstance(entry[field], str) or not entry[field].strip():
            raise IndiaSeriesError(f"{sid}: {field} must be text")
    if entry["group"] not in GROUPS:
        raise IndiaSeriesError(f"{sid}: group {entry['group']!r} is not one of {sorted(GROUPS)}")
    dataset = entry["dataset"]
    if dataset not in DATASETS:
        raise IndiaSeriesError(f"{sid}: dataset {dataset!r} is not one of {sorted(DATASETS)}")
    request, expect = entry["request"], entry["expect"]
    if not isinstance(request, dict) or not request or not all(
            isinstance(k, str) and isinstance(v, (str, int)) and not isinstance(v, bool) for k, v in request.items()):
        raise IndiaSeriesError(f"{sid}: request must map filter names to values")
    if {"limit", "page"} & set(request):
        raise IndiaSeriesError(f"{sid}: paging is added by the fetcher, not declared")
    if not isinstance(expect, dict) or not expect or not all(
            isinstance(k, str) and (v is None or isinstance(v, str)) for k, v in expect.items()):
        raise IndiaSeriesError(f"{sid}: expect must map field names to text or null")
    select = entry["select"]
    if not isinstance(select, dict) or not all(
            isinstance(k, str) and (v is None or isinstance(v, str)) for k, v in select.items()):
        raise IndiaSeriesError(f"{sid}: select must map field names to text or null (it may be empty)")
    if set(select) & set(expect):
        raise IndiaSeriesError(f"{sid}: a field cannot be both expected and selected")
    frequency, measures = DATASETS[dataset]
    if entry["measure"] not in measures:
        raise IndiaSeriesError(f"{sid}: measure {entry['measure']!r} is not one of {list(measures)} for {dataset}")
    if entry["status"] not in STATUSES:
        raise IndiaSeriesError(f"{sid}: status {entry['status']!r} is not one of {list(STATUSES)}")
    back = str(request.get("series", "")) == "Back"
    if back != (entry["status"] == "reconstructed"):
        raise IndiaSeriesError(f"{sid}: a back series must be declared reconstructed, and only a back series may be")
    return {"series_id": sid, "title": entry["title"].strip(), "factor_group": entry["group"], "dataset": dataset,
            "request": canonical({k: str(v) for k, v in request.items()}), "expect": canonical(expect),
            "row_select": canonical(select),
            "measure": entry["measure"], "unit": entry["unit"].strip(), "frequency": frequency,
            "status": entry["status"], "publisher": entry["publisher"].strip(), "licence": entry["licence"].strip()}


def sync_india_series(conn, path=SERIES_FILE):
    """Record every declared series not recorded yet; a recorded series must still be declared exactly as
    recorded. Returns the series ids added."""
    get_source(conn, SOURCE_ID)
    declared, expects = {}, {}
    for entry in load_series_file(path):
        row = check_entry(entry)
        if row["series_id"] in declared:
            raise IndiaSeriesError(f"{row['series_id']} is declared twice")
        key = (row["dataset"], row["request"])
        if expects.setdefault(key, row["expect"]) != row["expect"]:
            raise IndiaSeriesError(f"{row['series_id']}: series asking MoSPI the same request must expect the same fields")
        declared[row["series_id"]] = row
    cursor = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM mo_series")
    recorded = {r[0]: dict(zip(COLUMNS, r)) for r in cursor.fetchall()}
    for sid, stored in recorded.items():
        if sid not in declared:
            raise IndiaSeriesError(f"{sid} is recorded but no longer declared. Series are never silently changed.")
        changed = sorted(k for k in COLUMNS if stored[k] != declared[sid][k])
        if changed:
            raise IndiaSeriesError(f"{sid} differs from what is recorded in {changed}. Series are never silently changed:"
                                   " declare a changed series under a new id (ADR-009).")
    added = [sid for sid in declared if sid not in recorded]

    def work(c):
        for sid in added:
            c.execute(f"INSERT INTO mo_series ({', '.join(COLUMNS)}, source_id, recorded_at)"
                      f" VALUES ({', '.join('?' * len(COLUMNS))}, ?, ?)",
                      [declared[sid][k] for k in COLUMNS] + [SOURCE_ID, now_utc()])

    run_in_transaction(conn, work)
    return added


def india_series_info(conn, series_id):
    cursor = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM mo_series WHERE series_id = ?", [series_id])
    found = cursor.fetchone()
    if found is None:
        raise IndiaSeriesError(f"{series_id} is not a registered series - declare it in config/india_macro_series.yaml")
    return dict(zip(COLUMNS, found))


def registered_india_series(conn):
    return [r[0] for r in conn.execute("SELECT series_id FROM mo_series ORDER BY dataset, series_id")]


def requests_to_fetch(conn, series_ids=None):
    """The distinct (dataset, request) pairs behind the registered series (or behind series_ids)."""
    rows = conn.execute("SELECT series_id, dataset, request FROM mo_series ORDER BY dataset, request").fetchall()
    wanted = sorted({(d, r) for s, d, r in rows if series_ids is None or s in series_ids})
    return [(dataset, json.loads(request)) for dataset, request in wanted]


def page_params(request, page):
    return {**request, "limit": str(PAGE_SIZE), "page": str(page)}


# ---- reading answers ------------------------------------------------------------------------

def read_page(data, page):
    """(rows, paging) of one MoSPI answer page (bytes) that should be page number `page`, or an exception."""
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise MospiResponseError("Not MoSPI's JSON answer - refused, nothing stored") from None
    if not isinstance(doc, dict):
        raise MospiResponseError("Not MoSPI's answer: not an object")
    if "error" in doc:
        raise MospiResponseError(f"MoSPI answered with an error: {str(doc['error'])[:200]}")
    if doc.get("statusCode") is not True:
        raise MospiResponseError(f"MoSPI reported a failure: {str(doc.get('msg') or doc.get('message'))[:200]}")
    rows, meta = doc.get("data"), doc.get("meta_data")
    if not isinstance(rows, list) or not isinstance(meta, dict) or \
            any(type(meta.get(k)) is not int for k in META_KEYS):
        raise MospiResponseError("Not MoSPI's paged data list")
    if meta["totalRecords"] == 0:
        raise NoDataError("MoSPI's answer has no rows - nothing is stored")
    if meta["page"] != page:
        raise MospiResponseError(f"MoSPI answered page {meta['page']}, not page {page}")
    if not rows or not all(isinstance(r, dict) for r in rows):
        raise MospiResponseError(f"Page {page} holds no rows although MoSPI states {meta['totalRecords']}")
    return rows, meta


def period_of(dataset, row):
    """The first day of the row's month or financial-year quarter, as YYYY-MM-DD."""
    if dataset == "nas":
        match, quarter = FINANCIAL_YEAR.match(str(row.get("year"))), row.get("quarter")
        if not match or quarter not in QUARTER_START:
            raise RowRefused(f"not a financial-year quarter: {str(row.get('year'))[:12]!r} {str(quarter)[:4]!r}")
        first = int(match[1])
        if int(match[2]) != (first + 1) % 100:
            raise RowRefused(f"financial year {match[0]!r} is not two consecutive years")
        offset, month = QUARTER_START[quarter]
        return f"{first + offset:04d}-{month:02d}-01"
    year, month = str(row.get("year")), MONTHS.get(row.get("month"))
    if not re.fullmatch(r"\d{4}", year) or month is None:
        raise RowRefused(f"not a month: {year[:12]!r} {str(row.get('month'))[:12]!r}")
    return f"{year}-{month:02d}-01"


def _keep_page(c, path, retrieved_at, raw_dir):
    """(artifact id, newly stored) of one page; a page identical to one already kept reuses that artifact."""
    found = c.execute("SELECT artifact_id, source_id FROM raw_artifacts WHERE sha256 = ?",
                      [sha256_bytes(Path(path).read_bytes())]).fetchone()
    if found:
        if found[1] != SOURCE_ID:
            raise MospiResponseError("A page is identical to a file from another source - refused")
        return found[0], False
    return store_raw_artifact(c, SOURCE_ID, path, retrieved_at, raw_dir=raw_dir)[0], True


def load_mospi_pages(conn, dataset, request, pages, raw_dir=None):
    """Keep one complete read of one request - pages = [(path, retrieved_at), ...] in page order - and store
    the new vintages of every registered series it serves. Returns a report dict."""
    get_source(conn, SOURCE_ID)
    key = canonical({k: str(v) for k, v in request.items()})
    sids = [r[0] for r in conn.execute("SELECT series_id FROM mo_series WHERE dataset = ? AND request = ?"
                                       " ORDER BY series_id", [dataset, key])]
    if not sids:
        raise IndiaSeriesError(f"No registered series asks MoSPI for {dataset} {key}")
    series = [india_series_info(conn, sid) for sid in sids]
    expect = json.loads(series[0]["expect"])
    rows, totals = [], None
    for number, (path, _) in enumerate(pages, 1):
        page_rows, meta = read_page(Path(path).read_bytes(), number)
        if totals is None:
            totals = (meta["totalRecords"], meta["totalPages"])
        elif (meta["totalRecords"], meta["totalPages"]) != totals:
            raise MospiResponseError("The pages of one read disagree on the totals - refused")
        rows += page_rows
    if not pages or (len(rows), len(pages)) != totals:
        raise MospiResponseError(f"MoSPI's answer was cut short: {len(rows)} rows in {len(pages)} pages, but MoSPI"
                                 f" states {totals[0] if totals else '?'} rows in {totals[1] if totals else '?'}"
                                 " pages - refused")
    for number, row in enumerate(rows, 1):
        wrong = [k for k, v in expect.items() if row.get(k, MISSING) != v]
        if wrong:
            raise MospiResponseError(f"Row {number} does not match the request: {wrong[0]} is"
                                     f" {str(row.get(wrong[0], 'missing'))[:40]!r}, not {expect[wrong[0]]!r} -"
                                     " the filter was not applied; refused")
    retrieved = max(parse_timestamp(at) for _, at in pages)

    def work(c):
        kept = [_keep_page(c, path, at, raw_dir) for path, at in pages]
        if not any(new for _, new in kept):
            raise ArtifactError("Every page is identical to one already stored - nothing new")
        new, present, problems, not_given = [], 0, [], 0
        for info in series:
            sid, measure, select = info["series_id"], info["measure"], json.loads(info["row_select"])
            stored = {p: t for p, t in c.execute("SELECT period, value_text FROM mo_values WHERE series_id = ?"
                                                 " ORDER BY value_id", [sid])}
            seen, conflicted, aggregate_rows = {}, set(), 0
            for number, row in enumerate(rows, 1):
                if any(row.get(k, MISSING) != v for k, v in select.items()):
                    continue   # a breakdown row (e.g. one sub-industry), not the declared aggregate
                aggregate_rows += 1
                try:
                    period = period_of(dataset, row)
                    text = row.get(measure)
                    if text is None and measure in row:
                        not_given += 1   # MoSPI publishes no value here, e.g. no year-on-year rate in a base's first year
                        continue
                    if not isinstance(text, str) or not VALUE.match(text):
                        raise RowRefused(f"{measure} {str(text)[:20]!r} is not a number")
                except RowRefused as e:
                    problems.append(("row_refused", f"{sid} row {number}: {e}"))
                    continue
                if period in seen and seen[period] != text:
                    conflicted.add(period)
                seen.setdefault(period, text)
            if not aggregate_rows:
                problems.append(("no_aggregate_row", f"{sid}: no row in the answer is the declared aggregate {select}"))
            for period in sorted(conflicted):
                problems.append(("period_conflict", f"{sid} {period}: two different values in one answer - not stored"))
            for period, text in sorted(seen.items()):
                if period in conflicted:
                    continue
                if stored.get(period) == text:
                    present += 1
                else:
                    new.append([sid, period, float(text), text])
        read_id = c.execute(
            "INSERT INTO mo_reads (dataset, request, pages, rows, retrieved_at, values_recorded, already_present,"
            " problems, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [dataset, key, len(pages), len(rows), retrieved.isoformat(), len(new), present, len(problems),
             now_utc()]).lastrowid
        c.executemany("INSERT INTO mo_pages VALUES (?, ?, ?)",
                      [(read_id, n, artifact_id) for n, (artifact_id, _) in enumerate(kept, 1)])
        c.executemany("INSERT INTO mo_values (series_id, period, value, value_text, read_id, recorded_at)"
                      " VALUES (?, ?, ?, ?, ?, ?)", [v + [read_id, now_utc()] for v in new])
        c.executemany("INSERT INTO mo_problems VALUES (?, ?, ?)", [(read_id, k, d) for k, d in problems])
        shown = [f"{k}: {d}" for k, d in problems[:PROBLEMS_SHOWN]]
        if len(problems) > PROBLEMS_SHOWN:
            shown.append(f"... and {len(problems) - PROBLEMS_SHOWN} more (table mo_problems, read {read_id})")
        periods = [v[1] for v in new]
        return {"read_id": read_id, "series": sids, "pages": len(pages), "rows": len(rows), "values_recorded": len(new),
                "already_present": present, "values_not_given": not_given, "rows_refused": len(problems),
                "newest_period": max(periods) if periods else None, "problems": shown}

    return run_in_transaction(conn, work)


# ---- what was known at a decision time (5B) ---------------------------------------------------

def india_observations(conn, series_id, decision_time, claim=PitClaim.CURRENT_DECISION, start=None, end=None):
    """The series as known at decision_time, oldest period first: for each period the latest value read by
    then. Under historical replay nothing is returned - MoSPI gives no publication time, so availability stays
    in AVAILABILITY_REVIEW (5A.1, 5B.2)."""
    info = india_series_info(conn, series_id)
    known = {}
    for period, value, text, read_at in conn.execute(
            "SELECT v.period, v.value, v.value_text, r.retrieved_at FROM mo_values v"
            " JOIN mo_reads r ON r.read_id = v.read_id WHERE v.series_id = ?"
            " ORDER BY v.period, r.retrieved_at, v.value_id", [series_id]):
        if disposition(claim, decision_time, read_at, None) != Availability.ELIGIBLE:
            continue
        known[period] = {"series_id": series_id, "period": period, "value": value, "value_text": text,
                         "known_from": read_at, "status": info["status"], "unit": info["unit"]}
    return [known[p] for p in sorted(known) if (start is None or p >= start) and (end is None or p <= end)]


def india_latest(conn, series_id, decision_time, claim=PitClaim.CURRENT_DECISION):
    """The newest period known at decision_time, with its own period - never relabelled. None when nothing
    is known."""
    found = india_observations(conn, series_id, decision_time, claim)
    return found[-1] if found else None
