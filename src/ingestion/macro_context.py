"""Global and India macro context from FRED and its vintage archive ALFRED
(architecture 40B step 9a, 3B rule 4, 3G, 4C, 4G, 5, 5A, 5B, 5C; ADR-008).

Input: answers of FRED's API - a series' observations with their real-time periods, and the
series' description read right after them - fetched by the news fetcher, the only module allowed
to use the network. FRED's terms allow personal use, including series owned by others; S&P Dow
Jones Indices forbids reproduction of its indices, so they are refused. This product uses the
FRED(R) API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

Rules, each found on FRED's real answers (03-Oct-2026):
  - Series are declared by a person in config/macro_series.yaml and recorded once; a recorded
    series is never silently changed. Each records its market or publisher, calendar, time zone,
    session close (market closes), frequency, FRED's units and the owner's licence (5C rule 1).
  - Every answer is kept byte for byte before it is used. An answer that is not FRED's observation
    list for exactly what was asked, an error, an empty list or a list cut short is refused whole
    and nothing is stored - never 'no data' (4C.1). The series description must still match the
    registry (id, units, frequency): a change is refused, never loosened (4G rule 7).
  - Every value is a vintage (3G rule 1, 5A): what FRED showed for a date from a real-time start.
    A revision is a new vintage and old vintages stay - US payrolls for June 2026 had three
    vintages by October, US CPI for January 2020 six. The same date and start read again must
    agree, or it is a conflict and is recorded.
  - FRED refuses an answer spanning more than 2,000 vintage dates, and daily series gain about 255
    a year, so daily series are asked for a rolling three-year real-time window. FRED reports a
    value whose real start is earlier as starting on the window's first day: that start is marked
    clipped (the true start is that day or earlier) and never taken for a new vintage.
  - A date FRED lists without a value ('.') - US Labor Day for Treasury yields - is stored as
    structurally absent, never filled from another day (4C, 5C rule 4).
  - Where config/market_calendars.yaml declares a market's calendar for a series (Stage 10C-2), the
    calendar decides: a value on a day that market was closed is not a session close and is never
    used - FRED shows the Nasdaq on Good Friday 19-Apr-2019 and the Nikkei on 1-Oct-2020 (the Tokyo
    exchange's outage), each the previous close repeated - and no value on a day it traded is a
    conflict between the sources. The stored vintage is kept as FRED gave it.
  - Availability (5B, 5C). Current decisions: from our own retrieval. Historical replay: from
    FRED's own statement of its last update of the series, read right after the observations -
    every value in that answer was in FRED by then. ALFRED's vintage date is kept but is not proof:
    ICE's credit spread for 1-Oct-2026 carries the vintage date 1-Oct but FRED loaded it on 2-Oct
    at 09:12 Chicago time. History older than this system's first read is therefore not
    replayable yet.
  - A market close cannot be known before its session ended (5C). Its session close in its own
    time zone, in UTC, bounds availability from below; a row claiming a close was in FRED before
    the session ended is refused. A Nasdaq close dated 1 October is not available to an Indian
    decision on 1 October.
  - Nothing here is a covered security, a target or a benchmark, and a raw level is never a buy or
    sell signal on its own (3G rules 2-3).
"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from core.config import PROJECT_ROOT
from core.database import now_utc, run_in_transaction
from core.calendars import load_calendars
from core.dates import strict_iso_date
from core.sessions import ZONES, local_to_utc
from data_quality.missing_data import MissingClass
from data_quality.trust_chain import NoDataError
from ingestion.market_adapters import AdapterError
from ingestion.source_registry import get_source
from provenance.availability import Availability, PitClaim, disposition, parse_timestamp
from provenance.raw_store import sha256_bytes, store_raw_artifact

SOURCE_ID = "fred_alfred"
FRED_NOTICE = ("This product uses the FRED\u00ae API but is not endorsed or certified by the Federal Reserve"
               " Bank of St. Louis.")
SERIES_FILE = PROJECT_ROOT / "config" / "macro_series.yaml"
ENTRY_KEYS = {"series_id", "title", "group", "region", "kind", "market", "calendar", "time_zone", "frequency",
              "fred_units", "history_from", "licence"}
KINDS = ("market_close", "published_statistic")
GROUPS = ("rates_and_bonds", "currencies", "commodities", "world_equity_markets", "volatility_and_credit",
          "economic_releases")
FREQUENCIES = {"daily": "D", "daily_7day": "D", "weekly": "W", "monthly": "M", "quarterly": "Q"}
DAILY = ("daily", "daily_7day")
LOOKBACK = {"daily": timedelta(days=45), "daily_7day": timedelta(days=45), "weekly": timedelta(days=90),
            "monthly": timedelta(days=6 * 365), "quarterly": timedelta(days=6 * 365)}   # revisions reach back
VINTAGE_WINDOW = timedelta(days=3 * 365)   # FRED allows 2,000 vintage dates per answer
ALL_VINTAGES = "1776-07-04"                # FRED's earliest real-time date
OPEN_END = "9999-12-31"
EXCLUDED_SERIES = {"SP500", "DJIA", "DJCA", "DJTA", "DJUA"}
EXCLUDED_OWNER = "S&P Dow Jones Indices"   # forbids reproduction in any form without written permission
SERIES_ID = re.compile(r"^[A-Z0-9]{2,30}$")
ZONE_NAME = re.compile(r"^[A-Z][A-Za-z_]+/[A-Z][A-Za-z_]+$")
VALUE = re.compile(r"^-?\d+(\.\d+)?$")
NO_VALUE = "."
FRED_TIME = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})([+-])(\d{2})(?::?(\d{2}))?$")
OBS_HEADER = ("realtime_start", "realtime_end", "observation_start", "units", "output_type", "count", "offset",
              "observations")
ROW_KEYS = ("date", "value", "realtime_start", "realtime_end")
PROBLEMS_SHOWN = 10


class MacroSeriesError(Exception):
    """config/macro_series.yaml is invalid or disagrees with what is recorded."""


class MacroResponseError(AdapterError):
    """A FRED answer cannot be used as a whole. Nothing is stored."""


class RowRefused(ValueError):
    def __init__(self, kind, detail):
        super().__init__(detail)
        self.kind = kind


# ---- the series registry ----------------------------------------------------------------

def load_series_file(path=SERIES_FILE):
    with open(Path(path), encoding="utf-8-sig") as f:
        data = yaml.safe_load(f) or {}
    return data.get("series") or []


def check_entry(entry):
    """One declared series as stored, or MacroSeriesError."""
    if not isinstance(entry, dict):
        raise MacroSeriesError(f"Each series must be a set of fields: {entry!r}")
    name = entry.get("series_id")
    keys = set(entry) - {"session_close"}
    if keys != ENTRY_KEYS:
        raise MacroSeriesError(f"{name}: missing fields {sorted(ENTRY_KEYS - keys)}, unknown fields"
                               f" {sorted(keys - ENTRY_KEYS)}")
    row = {k: str(entry[k]).strip() if entry[k] is not None else "" for k in ENTRY_KEYS}
    empty = sorted(k for k, v in row.items() if not v)
    if empty:
        raise MacroSeriesError(f"{name}: empty fields {empty}")
    sid = row["series_id"]
    if not SERIES_ID.match(sid):
        raise MacroSeriesError(f"{sid!r} is not a FRED series id (capital letters and digits)")
    if sid in EXCLUDED_SERIES:
        raise MacroSeriesError(f"{sid} is not allowed: {EXCLUDED_OWNER} forbids reproduction without written"
                               " permission (ADR-008)")
    for field, allowed in (("kind", KINDS), ("group", GROUPS), ("frequency", FREQUENCIES)):
        if row[field] not in allowed:
            raise MacroSeriesError(f"{sid}: {field} {row[field]!r} is not one of {sorted(allowed)}")
    try:
        first = strict_iso_date(row["history_from"])
    except ValueError:
        raise MacroSeriesError(f"{sid}: history_from must be a YYYY-MM-DD date") from None
    close = entry.get("session_close")
    if row["kind"] == "market_close":
        if row["time_zone"] not in ZONES:
            raise MacroSeriesError(f"{sid}: a market close needs a time zone declared in core/sessions.py,"
                                   f" not {row['time_zone']!r}")
        if row["frequency"] != "daily":
            raise MacroSeriesError(f"{sid}: a market close must be a daily (business-day) series")
        try:
            local_to_utc(max(first, strict_iso_date("2007-03-11")), close, row["time_zone"])
        except ValueError as e:
            raise MacroSeriesError(f"{sid}: session_close {close!r} cannot be placed in time: {e}") from None
        row["session_close"] = close
    else:
        if close is not None:
            raise MacroSeriesError(f"{sid}: only a market close has a session_close")
        if not (row["time_zone"] in ZONES or ZONE_NAME.match(row["time_zone"])):
            raise MacroSeriesError(f"{sid}: {row['time_zone']!r} is not a time zone name like Area/City")
        row["session_close"] = None
    row["history_from"] = first.isoformat()
    return row


COLUMNS = ("series_id", "title", "factor_group", "region", "kind", "market", "calendar", "time_zone",
           "session_close", "frequency", "fred_units", "history_from", "licence")


def _as_columns(row):
    return {**{k: row[k] for k in COLUMNS if k != "factor_group"}, "factor_group": row["group"]}


def sync_series(conn, path=SERIES_FILE):
    """Record every declared series not recorded yet. A recorded series must still be declared exactly
    as recorded: series are never silently changed. Returns the series ids added."""
    get_source(conn, SOURCE_ID)
    declared = {}
    for entry in load_series_file(path):
        row = _as_columns(check_entry(entry))
        if row["series_id"] in declared:
            raise MacroSeriesError(f"{row['series_id']} is declared twice")
        declared[row["series_id"]] = row
    cursor = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM mc_series")
    recorded = {r[0]: dict(zip(COLUMNS, r)) for r in cursor.fetchall()}
    for sid, stored in recorded.items():
        if sid not in declared:
            raise MacroSeriesError(f"{sid} is recorded but no longer declared. Series are never silently changed.")
        changed = sorted(k for k in COLUMNS if stored[k] != declared[sid][k])
        if changed:
            raise MacroSeriesError(f"{sid} differs from what is recorded in {changed}. Series are never silently"
                                   " changed: declare a changed series under a new registration (ADR-008).")
    added = [sid for sid in declared if sid not in recorded]

    def work(c):
        for sid in added:
            row = declared[sid]
            c.execute(f"INSERT INTO mc_series ({', '.join(COLUMNS)}, source_id, recorded_at)"
                      f" VALUES ({', '.join('?' * len(COLUMNS))}, ?, ?)",
                      [row[k] for k in COLUMNS] + [SOURCE_ID, now_utc()])

    run_in_transaction(conn, work)
    return added


def series_info(conn, series_id):
    cursor = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM mc_series WHERE series_id = ?", [series_id])
    found = cursor.fetchone()
    if found is None:
        raise MacroSeriesError(f"{series_id} is not a registered series - declare it in config/macro_series.yaml")
    return dict(zip(COLUMNS, found))


def registered_series(conn):
    return [r[0] for r in conn.execute("SELECT series_id FROM mc_series ORDER BY factor_group, series_id")]


# ---- what to ask FRED --------------------------------------------------------------------

def request_for(conn, series_id, today, full=False):
    """(observations request, description request) for the next fetch of a series; today is a date."""
    info = series_info(conn, series_id)
    first = strict_iso_date(info["history_from"])
    last = conn.execute("SELECT MAX(obs_date) FROM mc_vintages WHERE series_id = ?", [series_id]).fetchone()[0]
    start = first if full or last is None else max(first, strict_iso_date(last) - LOOKBACK[info["frequency"]])
    realtime_start = (today - VINTAGE_WINDOW).isoformat() if info["frequency"] in DAILY else ALL_VINTAGES
    return ({"series_id": series_id, "observation_start": start.isoformat(), "realtime_start": realtime_start,
             "realtime_end": OPEN_END}, {"series_id": series_id})


# ---- reading answers ------------------------------------------------------------------------

def _json(data, what):
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise MacroResponseError(f"Not FRED's JSON {what} - refused, nothing stored") from None
    if not isinstance(doc, dict):
        raise MacroResponseError(f"Not FRED's {what}: the answer is not an object")
    if "error_code" in doc or "error_message" in doc:
        raise MacroResponseError(f"FRED answered with an error: {str(doc.get('error_message'))[:200]}")
    return doc


def read_observations(data, asked):
    """The rows of one FRED observations answer (bytes) for the request asked, or an exception."""
    doc = _json(data, "observations")
    missing = [k for k in OBS_HEADER if k not in doc]
    if missing:
        raise MacroResponseError(f"Not FRED's observation list: no {missing}")
    for key in ("realtime_start", "realtime_end", "observation_start"):
        if doc[key] != asked[key]:
            raise MacroResponseError(f"FRED answered for {key} {doc[key]!r}, not the {asked[key]!r} asked for")
    if doc["units"] != "lin" or doc["output_type"] != 1 or doc["offset"] != 0:
        raise MacroResponseError("FRED's answer is not plain levels by real-time period from the first row")
    rows = doc["observations"]
    if not isinstance(rows, list):
        raise MacroResponseError("Not FRED's observation list: observations is not a list")
    if not rows:
        raise NoDataError("FRED's answer has no observations - nothing is stored")
    if doc["count"] != len(rows):
        raise MacroResponseError(f"FRED's answer was cut short: {len(rows)} of {doc['count']} rows - refused")
    return rows


def fred_time(text):
    """FRED's 'last_updated' text, e.g. '2026-10-02 15:16:37-05', as a datetime with its offset."""
    match = FRED_TIME.match(text) if isinstance(text, str) else None
    if not match:
        raise ValueError(f"Not FRED's time format: {str(text)[:40]!r}")
    day = strict_iso_date(match[1])
    offset = timedelta(hours=int(match[6]), minutes=int(match[7] or 0)) * (-1 if match[5] == "-" else 1)
    return datetime(day.year, day.month, day.day, int(match[2]), int(match[3]), int(match[4]),
                    tzinfo=timezone(offset))


def read_series_meta(data, info, retrieved_at):
    """FRED's description of one series (bytes), checked against the registry, or an exception."""
    doc = _json(data, "series description")
    found = doc.get("seriess")
    if not isinstance(found, list) or len(found) != 1 or not isinstance(found[0], dict):
        raise MacroResponseError("Not FRED's description of one series")
    meta, sid = found[0], info["series_id"]
    if meta.get("id") != sid:
        raise MacroResponseError(f"FRED described {str(meta.get('id'))[:30]!r}, not {sid}")
    if EXCLUDED_OWNER in str(meta.get("notes") or ""):
        raise MacroResponseError(f"{sid} is owned by {EXCLUDED_OWNER}, whose terms forbid reproduction - refused")
    if meta.get("units") != info["fred_units"]:
        raise MacroResponseError(f"FRED describes {sid}'s units as {str(meta.get('units'))[:60]!r}, the registry"
                                 f" says {info['fred_units']!r} - refused; a changed series needs a new registration")
    if meta.get("frequency_short") != FREQUENCIES[info["frequency"]]:
        raise MacroResponseError(f"FRED gives {sid} the frequency {str(meta.get('frequency'))[:30]!r}, the registry"
                                 f" says {info['frequency']!r} - refused")
    try:
        updated = fred_time(meta.get("last_updated"))
    except ValueError as e:
        raise MacroResponseError(f"{sid}: {e}") from None
    if updated > parse_timestamp(retrieved_at):
        raise MacroResponseError(f"{sid}: FRED's last update {updated.isoformat()} is later than our read of it")
    return {"updated": updated, "title": str(meta.get("title") or ""), "units": meta["units"]}


def _parse_row(r, info, asked_start, read_day, proven):
    """(date, value, text, realtime start, realtime end, clipped, set_at) of one answer row, or RowRefused."""
    if not isinstance(r, dict) or any(k not in r for k in ROW_KEYS):
        raise RowRefused("row_refused", f"a row without {list(ROW_KEYS)}")
    try:
        day, start, end = (strict_iso_date(r[k]) for k in ("date", "realtime_start", "realtime_end"))
    except ValueError as e:
        raise RowRefused("row_refused", str(e)) from None
    if end < start:
        raise RowRefused("row_refused", f"{day}: real-time end {end} is before its start {start}")
    if r["realtime_start"] < asked_start:
        raise RowRefused("row_refused", f"{day}: real-time start {start} is before the window asked for")
    if start > read_day + timedelta(days=1):
        raise RowRefused("row_refused", f"{day}: real-time start {start} is after this answer was read")
    frequency = info["frequency"]
    if (frequency in ("monthly", "quarterly") and day.day != 1) or (frequency == "quarterly" and day.month % 3 != 1):
        raise RowRefused("row_refused", f"{day} is not the first day of a {frequency[:-2]}")
    text = r["value"]
    if text == NO_VALUE:
        value = None
    elif isinstance(text, str) and VALUE.match(text):
        value = float(text)
    else:
        raise RowRefused("row_refused", f"{day}: value {str(text)[:20]!r} is not a number")
    set_at = None
    if info["kind"] == "market_close":
        try:
            set_at = local_to_utc(day, info["session_close"], info["time_zone"])
        except ValueError as e:
            raise RowRefused("row_refused", f"{day}: {e}") from None
        if proven < set_at:
            raise RowRefused("published_before_close", f"{day}: FRED shows this close by"
                             f" {proven:%Y-%m-%d %H:%M} UTC, before that session ended ({set_at:%Y-%m-%d %H:%M} UTC)")
    return day.isoformat(), value, text, start.isoformat(), end.isoformat(), int(r["realtime_start"] == asked_start), \
        set_at


def _keep_description(c, path, retrieved_at, raw_dir):
    """The raw artifact holding this series description - stored once, reused when unchanged."""
    found = c.execute("SELECT artifact_id, source_id FROM raw_artifacts WHERE sha256 = ?",
                      [sha256_bytes(Path(path).read_bytes())]).fetchone()
    if found:
        if found[1] != SOURCE_ID:
            raise MacroResponseError("This description is identical to a file from another source - refused")
        return found[0]
    return store_raw_artifact(c, SOURCE_ID, path, retrieved_at, raw_dir=raw_dir)[0]


def load_fred_answers(conn, series_id, obs_path, obs_retrieved_at, meta_path, meta_retrieved_at, asked,
                      raw_dir=None):
    """Keep one FRED observations answer and the series description read right after it, and store the
    vintages it carries. Returns a report dict."""
    get_source(conn, SOURCE_ID)
    info = series_info(conn, series_id)
    obs_path, meta_path = Path(obs_path), Path(meta_path)
    rows = read_observations(obs_path.read_bytes(), asked)
    obs_at, meta_at = parse_timestamp(obs_retrieved_at), parse_timestamp(meta_retrieved_at)
    if meta_at < obs_at:
        raise MacroResponseError("The series description must be read after the observations")
    meta = read_series_meta(meta_path.read_bytes(), info, meta_at)
    proven = min(meta["updated"], obs_at).astimezone(timezone.utc)
    read_day = obs_at.astimezone(timezone.utc).date()

    def work(c):
        artifact_id, _ = store_raw_artifact(
            c, SOURCE_ID, obs_path, obs_at, published_at=proven,
            publication_evidence=f"FRED's last update of {series_id} ({meta['updated'].isoformat()}), read right after"
                                 " this answer, or this read if earlier")
        meta_artifact_id = _keep_description(c, meta_path, meta_at, raw_dir)
        known = {}
        for d, rs, text in c.execute("SELECT obs_date, realtime_start, value_text FROM mc_vintages"
                                     " WHERE series_id = ? ORDER BY realtime_start", [series_id]):
            known.setdefault(d, []).append((rs, text))
        new, present, problems = [], 0, []
        for number, raw in enumerate(rows, 1):
            try:
                day, value, text, start, end, clipped, set_at = _parse_row(raw, info, asked["realtime_start"],
                                                                         read_day, proven)
            except RowRefused as e:
                problems.append((e.kind, f"row {number}: {e}"))
                continue
            held = known.get(day, [])
            same_start = [t for s, t in held if s == start]
            inside = [t for s, t in held if start <= s <= end and t != text]
            in_effect = [t for s, t in held if s <= start]
            if same_start and same_start[0] == text:
                present += 1
            elif same_start or inside:
                problems.append(("vintage_conflict", f"row {number}: {day} from {start} was read before with a"
                                 " different value"))
            elif clipped and in_effect and in_effect[-1] == text:
                present += 1
            else:
                known.setdefault(day, []).append((start, text))
                known[day].sort()
                new.append([series_id, day, value, MissingClass.STRUCTURALLY_ABSENT.value if value is None else None,
                            text, start, clipped, set_at.isoformat() if set_at else None, proven.isoformat()])
        response_id = c.execute(
            "INSERT INTO mc_responses (series_id, artifact_id, meta_artifact_id, request, meta_retrieved_at,"
            " series_updated_at, rows, vintages_recorded, already_present, rows_refused, recorded_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [series_id, artifact_id, meta_artifact_id, json.dumps(asked, sort_keys=True), meta_at.isoformat(),
             meta["updated"].isoformat(), len(rows), len(new), present, len(problems), now_utc()]).lastrowid
        c.executemany("INSERT INTO mc_vintages (series_id, obs_date, value, missing_class, value_text,"
                      " realtime_start, start_clipped, set_at, available_at, response_id, recorded_at)"
                      " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [v + [response_id, now_utc()] for v in new])
        c.executemany("INSERT INTO mc_problems VALUES (?, ?, ?)", [(response_id, k, d) for k, d in problems])
        shown = [f"{k}: {d}" for k, d in problems[:PROBLEMS_SHOWN]]
        if len(problems) > PROBLEMS_SHOWN:
            shown.append(f"... and {len(problems) - PROBLEMS_SHOWN} more (table mc_problems, answer {response_id})")
        dated = [r[1] for r in new if r[2] is not None]
        return {"response_id": response_id, "rows": len(rows), "vintages_recorded": len(new),
                "already_present": present, "rows_refused": len(problems), "newest_date": max(dated) if dated else None,
                "fred_updated": meta["updated"].isoformat(), "problems": shown}

    return run_in_transaction(conn, work)


# ---- what was known at a decision time (5B, 5C) -----------------------------------------------

def _calendar_for(info):
    """The market calendar that decides this series' trading days (Stage 10C-2), or None."""
    calendars, mapping = load_calendars()
    cid = mapping.get(info["series_id"])
    if cid is None:
        return None
    cal = calendars[cid]
    if info["kind"] != "market_close" or info["time_zone"] != cal.time_zone:
        raise MacroSeriesError(f"{info['series_id']} is mapped to calendar {cid}, but it is not a market close in"
                               f" {cal.time_zone}")
    return cal


def _by_calendar(row, cal):
    """A vintage judged by its market's calendar (5C rule 4): a value on a day the market was closed is not a
    session close and is never used; no value on a day the market traded is a conflict between the sources."""
    if cal is None or not cal.covers(row["date"]):
        return row
    if not cal.is_session(row["date"]) and row["value"] is not None:
        return {**row, "value": None, "missing_class": MissingClass.STRUCTURALLY_ABSENT,
                "reason": f"{cal.calendar_id} was closed that day; FRED's value {row['value_text']} is not a session close"}
    if cal.is_session(row["date"]) and row["value"] is None:
        return {**row, "missing_class": MissingClass.SOURCE_CONFLICT,
                "reason": f"{cal.calendar_id} traded that day but FRED lists no value"}
    return row


def _known_at(conn, series_id, decision_time, claim):
    """{date: the latest vintage of that date known at decision_time under the claim}, judged by the series'
    market calendar where one is declared."""
    cal = _calendar_for(series_info(conn, series_id))
    decision = parse_timestamp(decision_time)
    known = {}
    for row in conn.execute(
            "SELECT v.obs_date, v.value, v.missing_class, v.value_text, v.realtime_start, v.start_clipped, v.set_at,"
            " v.available_at, a.retrieved_at FROM mc_vintages v JOIN mc_responses r ON r.response_id = v.response_id"
            " JOIN raw_artifacts a ON a.artifact_id = r.artifact_id WHERE v.series_id = ?"
            " ORDER BY v.obs_date, v.realtime_start, v.vintage_id", [series_id]):
        day, value, missing, text, start, clipped, set_at, available_at, retrieved_at = row
        if disposition(claim, decision, retrieved_at, available_at) != Availability.ELIGIBLE:
            continue
        if set_at and parse_timestamp(set_at) > decision:   # 5C: never before the session ended
            continue
        basis = retrieved_at if PitClaim(claim) == PitClaim.CURRENT_DECISION else available_at
        known[day] = {"series_id": series_id, "date": day, "value": value,
                      "missing_class": MissingClass(missing) if missing else None, "value_text": text,
                      "realtime_start": start, "start_clipped": bool(clipped), "set_at": set_at,
                      "available_at": basis}
    return {day: _by_calendar(row, cal) for day, row in known.items()}


def observations(conn, series_id, decision_time, claim=PitClaim.CURRENT_DECISION, start=None, end=None):
    """The series as known at decision_time under the claim, oldest date first: for each date the
    latest vintage known then. Dates without a value carry their missing-data class."""
    known = _known_at(conn, series_id, decision_time, claim)
    return [known[d] for d in sorted(known) if (start is None or d >= start) and (end is None or d <= end)]


def latest(conn, series_id, decision_time, claim=PitClaim.CURRENT_DECISION):
    """The newest dated value known at decision_time, with its own date and age in days - never
    relabelled as a later date. None when nothing is known."""
    known = _known_at(conn, series_id, decision_time, claim)
    dated = [d for d in sorted(known) if known[d]["value"] is not None]
    if not dated:
        return None
    found = dict(known[dated[-1]])
    found["age_days"] = (parse_timestamp(decision_time).date() - strict_iso_date(found["date"])).days
    found["later_dates_without_value"] = [d for d in sorted(known) if d > dated[-1]]
    return found


def value_on(conn, series_id, day, decision_time, claim=PitClaim.CURRENT_DECISION):
    """The value for exactly one date as known at decision_time, or why there is none (4C, 5C rule 4).
    Another date's value is never carried forward."""
    info = series_info(conn, series_id)
    wanted = strict_iso_date(day) if isinstance(day, str) else day
    if (info["frequency"] in ("monthly", "quarterly") and wanted.day != 1) or \
            (info["frequency"] == "quarterly" and wanted.month % 3 != 1):
        raise ValueError(f"{series_id} is dated by the first day of each {info['frequency'][:-2]}, not {wanted}")
    known = _known_at(conn, series_id, decision_time, claim)
    key = wanted.isoformat()
    if key in known:
        found = dict(known[key])
        if found["value"] is None:
            found.setdefault("reason", "FRED lists this date without a value: the market or publisher had none that day")
        return found
    dates = sorted(known)
    cal = _calendar_for(info)
    if cal is not None and cal.covers(wanted):
        if not cal.is_session(wanted):
            cls, reason = MissingClass.STRUCTURALLY_ABSENT, f"{cal.calendar_id} was closed that day"
        elif not dates or key > dates[-1]:
            cls, reason = MissingClass.NOT_YET_RELEASED, "not published as far as was known at the decision time"
        else:
            cls, reason = MissingClass.EXTRACTION_FAILURE, f"{cal.calendar_id} traded but no row is stored for this date"
    elif info["frequency"] == "daily" and wanted.weekday() >= 5:
        cls, reason = MissingClass.STRUCTURALLY_ABSENT, "a weekend: this series has values on business days only"
    elif not dates or key > dates[-1]:
        cls, reason = MissingClass.NOT_YET_RELEASED, "not published as far as was known at the decision time"
    elif key < dates[0]:
        cls, reason = MissingClass.EXTRACTION_FAILURE, f"before the stored history (first date {dates[0]})"
    else:
        cls, reason = MissingClass.EXTRACTION_FAILURE, "FRED's answers carried no row for this date"
    return {"series_id": series_id, "date": key, "value": None, "missing_class": cls, "reason": reason}
