"""Macro and geopolitical events - events with no issuer (architecture 40B step 9b, 3G, 4A.0, 4A rule 5,
4C.1, 4D, 4E, 4G, 5B, 5C; ADR-010).

Inputs:
  - three central banks' official feeds, read by the news fetcher (the only network module): the Federal
    Reserve's monetary-policy press releases, the ECB's press releases and the Bank of Japan's
    what's-new feed in English;
  - FRED's release calendar for the declared US releases (dates only, no time of day);
  - events derived from data this system already stores: the first release of each new period of the
    headline US and India statistics (FRED, MoSPI) and SEBI's circulars;
  - events declared by the owner in config/declared_events.yaml, each citing a public source - for what
    no official feed brings in (Union Budget, RBI decisions, elections, OPEC+, ratings, conflicts).

Rules, each found on the real feeds and answers of 04-Oct-2026:
  - Each feed is RSS 2.0 with a title, a link and a pubDate carrying a time of day and a zone (Fed 'GMT',
    ECB '+0200', BoJ '+0900'). A read is kept byte for byte. A feed with no items, anything that is not
    RSS 2.0, or a feed declaring a DOCTYPE or ENTITY is refused whole and nothing is stored (4C.1); the
    BoJ's 'Network Busy' page is such a refusal, never 'no news'.
  - An item is stored once per feed, by its link; read again differently it is a conflict and is
    recorded. Items are refused, and recorded, for no title, a link off the issuer's own site, a pubDate
    without time or zone (or '-0000'), a weekday that contradicts the date, or a time after the read.
  - A read sharing no item with the previous read of the same feed says that items may have been
    missed (4E): the Fed feed keeps about six months, the BoJ's about four weeks, the ECB's ten days.
  - Availability (5B): current decisions use this system's first read of an item. Historical replay
    uses the issuer's own stated release time - accepted only with a time of day and a zone and never
    later than our read (owner decision 04-Oct-2026, ADR-010), as NSE's dissemination time is.
  - Types (rule me-types-1), from the issuer's own words only - never guessed: the Fed's FOMC statement
    is always titled 'Federal Reserve issues FOMC statement' (18:00 GMT, 2 pm New York); the ECB's
    decision carries document code 'mp' (ecb.mp260910...) and its combined statement 'ds'; the BoJ's
    statements on monetary policy are files k<yymmdd><letter> under /en/mopo/mpmdeci/, and a title
    'Change in the Guideline for Money Market Operations' says the policy rate changed. Minutes,
    projections, speeches and interviews are communication; everything else stays unclassified.
  - On 18-Sep-2026 the BoJ's English feed carried only the '(Reference)' statement (k260918b), not the
    main one (k260918a): a BoJ decision appears when any of its statement files appears, and a meeting
    whose files never appear in the feed is missed (not claimed).
  - One meeting, one event (rule me-dedup-1): decision items of one central bank for the same meeting
    date are one event; items not yet known at the decision time are left out before grouping.
  - FRED's release calendar is a snapshot per read: the schedule known at a decision time is the latest
    read by then. A date added or dropped inside the span both reads cover is a schedule change and is
    recorded - the US shutdown of late 2025 moved CPI from November to 18-Dec-2025. FRED's 'FOMC Press
    Release' lists every day of the year and is not used as a meeting calendar.
  - Data releases (rule me-releases-1): the first vintage of each new period of a declared FRED series
    is a 'major data release'; its ALFRED real-time start is the stated release date (it equals FRED's
    calendar: CPI for Aug-2026 on 2026-09-11). Availability is the vintage's own (10C). A period FRED lists
    without a value is no release: BLS never published October 2025 CPI (the shutdown), FRED shows '.'.
    MoSPI gives no release time: the history in a series' first read says nothing about when it came out,
    so only a period that is new in a later read is a release - released after the previous read and
    known from this one, for current decisions only.
    Surprise against consensus is never assessed: no licensed consensus exists (4A.0).
  - SEBI's circulars that name no company are 'sector-wide regulation' (rule me-sebi-1).
  - Declared events are recorded once and never silently changed; they are known from the moment they
    are recorded, for current decisions only.
  - Titles are data, never instruction (4D). No event carries an issuer; it reaches a security only
    through a declared, recorded route (ingestion/event_routes.py, 4A rule 5).
"""
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from core.config import PROJECT_ROOT
from core.database import now_utc, run_in_transaction
from core.dates import strict_iso_date
from data_quality.extraction_confidence import ExtractionConfidence
from data_quality.trust_chain import NoDataError
from ingestion.market_adapters import AdapterError
from ingestion.nse_announcements import REGISTERED_TYPES as ISSUER_EVENT_TYPES
from ingestion.sebi_releases import releases as sebi_releases
from ingestion.source_registry import get_source
from provenance.availability import Availability, PitClaim, disposition, parse_timestamp
from provenance.raw_store import store_raw_artifact

NOT_ASSESSED = "not_assessed"
TYPES_RULE = "me-types-1"
DEDUP_RULE = "me-dedup-1"
RELEASES_RULE = "me-releases-1"
SEBI_RULE = "me-sebi-1"
DECLARED_RULE = "me-declared-1"
PROBLEMS_SHOWN = 10

MACRO_EVENT_TYPES = {   # architecture 4A.0 - the five groups added in v2.2.0 (ACR-105)
    "monetary_policy_and_rates": {"central_bank_decision", "policy_rate_change", "liquidity_measure",
                                  "sovereign_bond_auction_stress"},
    "fiscal_trade_and_regulation": {"union_budget", "tax_or_gst_change", "tariff_or_trade_action",
                                    "export_or_import_restriction", "production_linked_incentive",
                                    "sector_wide_regulation"},
    "sovereign_and_macro_data": {"sovereign_rating_action", "major_data_release"},
    "geopolitics_and_shocks": {"armed_conflict_onset", "armed_conflict_escalation", "ceasefire", "sanctions",
                               "opec_decision", "supply_disruption", "natural_disaster", "monsoon_deviation",
                               "pandemic_measures", "election_result"},
    "index_provider_and_flow_events": {"index_provider_country_change", "foreign_flow_episode"},
}
MACRO_TYPES = frozenset().union(*MACRO_EVENT_TYPES.values())
GROUP_OF = {t: g for g, types in MACRO_EVENT_TYPES.items() for t in types}
REGIONS = ("India", "United States", "Euro area", "Japan", "China", "United Kingdom", "Middle East", "Russia",
           "Other Asia", "Other Europe", "World")

ATTRIBUTION = ("Sources: Board of Governors of the Federal Reserve System; European Central Bank (this information"
               " is available free of charge at www.ecb.europa.eu); Bank of Japan.")
FEEDS = {   # source_id -> the issuing institution, its region and its own site (every item link must be on it)
    "fed_monetary_feed": {"institution": "Federal Reserve", "region": "United States",
                          "site": re.compile(r"^https://www\.federalreserve\.gov/\S+$")},
    "ecb_press_feed": {"institution": "European Central Bank", "region": "Euro area",
                       "site": re.compile(r"^https://www\.ecb\.europa\.eu/\S+$")},
    "boj_whatsnew_feed": {"institution": "Bank of Japan", "region": "Japan",
                          "site": re.compile(r"^https?://www\.boj\.or\.jp/\S+$")},
}

# ---- rule me-types-1: the issuer's own words -------------------------------------------------------
FED_RELEASE = re.compile(r"^https://www\.federalreserve\.gov/newsevents/pressreleases/monetary(\d{8})[a-z]\.htm$")
FED_DECISION_TITLE = "Federal Reserve issues FOMC statement"
FED_COMMUNICATION = re.compile(r"^(Minutes of the (Federal Open Market Committee|Board)\b|.*\beconomic projections\b)")
ECB_CODE = re.compile(r"^https://www\.ecb\.europa\.eu/+press/\S*/ecb\.([a-z]{2})(\d{6})[~_.]")
ECB_DECISION_CODES = frozenset({"mp", "ds"})            # monetary policy decisions; combined decisions and statement
ECB_COMMUNICATION_CODES = frozenset({"sp", "in", "mg", "is"})   # speeches, interviews, accounts, press conferences
BOJ_STATEMENT = re.compile(r"^https?://www\.boj\.or\.jp/en/mopo/mpmdeci/(?:mpr|state)_\d{4}/k(\d{6})[a-z]\.(?:pdf|htm)$")
BOJ_COMMUNICATION = re.compile(r"^https?://www\.boj\.or\.jp/en/mopo/mpmsche_minu/")
BOJ_RATE_CHANGE_TITLE = "Change in the Guideline for Money Market Operations"

PUB_DATE = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                      r" (\d{4}) (\d{2}):(\d{2}):(\d{2}) (GMT|UTC|[+-]\d{4})$")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# ---- FRED's release calendar and the derived data releases ------------------------------------------
CALENDAR_SOURCE = "fred_release_calendar"
CALENDAR_LIMIT = 40
CALENDAR_KEYS = ("realtime_start", "realtime_end", "order_by", "sort_order", "count", "offset", "limit",
                 "release_dates")
CALENDAR_RELEASES = {   # FRED release id -> (FRED's release name, region, the declared FRED series it publishes)
    10: ("Consumer Price Index", "United States", "CPIAUCSL"),
    50: ("Employment Situation", "United States", "PAYEMS"),
    53: ("Gross Domestic Product", "United States", "GDPC1"),
}
FRED_RELEASE_SERIES = {   # FRED series -> what its first vintage of a period announces
    "CPIAUCSL": "US consumer prices (CPI)",
    "PAYEMS": "US payroll employment (Employment Situation)",
    "GDPC1": "US real GDP",
}
MOSPI_RELEASE_SERIES = {
    "IN_CPI24_GEN_INDEX": "India consumer prices (CPI, base 2024)",
    "IN_IIP2223_GEN_INDEX": "India industrial production (IIP, base 2022-23)",
    "IN_GDP2223_Q_REAL": "India real GDP (base 2022-23)",
}
SURPRISE = "not_assessed: no licensed consensus exists (4A.0)"

# ---- declared events -------------------------------------------------------------------------------
DECLARED_FILE = PROJECT_ROOT / "config" / "declared_events.yaml"
DECLARED_SOURCE = "declared_by_owner"
DECLARED_KEYS = {"event_key", "event_type", "region", "institution", "occurred_on", "occurred_at", "title",
                 "source", "source_url", "declared_on"}
DECLARED_REQUIRED = {"event_key", "event_type", "region", "occurred_on", "title", "source", "declared_on"}
EVENT_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{2,60}$")
SOURCE_URL = re.compile(r"^https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/\S*)?$")
RBI_URL = re.compile(r"^https://([A-Za-z0-9-]+\.)*rbi\.org\.in(/|$)", re.I)   # ADR-006: RBI is not used


class EventFeedError(AdapterError):
    """A central bank's feed cannot be used as a whole. Nothing is stored."""


class CalendarResponseError(AdapterError):
    """FRED's release-calendar answer cannot be used as a whole. Nothing is stored."""


class DeclaredEventError(Exception):
    """config/declared_events.yaml cannot be used as it is. Nothing is recorded."""


# ---- central-bank feeds ----------------------------------------------------------------------------

def parse_pub_date(text):
    """An RSS pubDate with a time of day and a zone, as an aware datetime in UTC; otherwise ValueError."""
    match = PUB_DATE.match(text or "")
    if not match:
        raise ValueError(f"not a pubDate with time and zone: {str(text)[:40]!r}")
    weekday, day, month, year, hh, mm, ss, zone = match.groups()
    if zone in ("GMT", "UTC"):
        offset = timedelta(0)
    elif zone == "-0000":
        raise ValueError(f"the zone of {text!r} is unknown ('-0000')")
    else:
        sign = 1 if zone[0] == "+" else -1
        offset = sign * timedelta(hours=int(zone[1:3]), minutes=int(zone[3:5]))
    stated = datetime(int(year), MONTHS.index(month) + 1, int(day), int(hh), int(mm), int(ss),
                      tzinfo=timezone(offset))
    if WEEKDAYS[stated.weekday()] != weekday:
        raise ValueError(f"{text!r}: the weekday does not match the date")
    return stated.astimezone(timezone.utc)


def read_feed(data):
    """The items of one central-bank feed (bytes) as [(title, link, pubDate text)], or an exception."""
    if b"<!DOCTYPE" in data[:2000].upper() or b"<!ENTITY" in data.upper():
        raise EventFeedError("The feed declares a DOCTYPE or ENTITY - refused, nothing stored")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise EventFeedError(f"Not an RSS feed: {e}") from None
    channel = root.find("channel")
    if root.tag != "rss" or root.get("version") != "2.0" or channel is None:
        raise EventFeedError(f"Not an RSS 2.0 feed: the document is <{root.tag}>")
    items = channel.findall("item")
    if not items:
        raise NoDataError("The feed has no items - nothing is stored")
    return [((i.findtext("title") or "").strip(), (i.findtext("link") or "").strip(),
             (i.findtext("pubDate") or "").strip()) for i in items]


def _parse_item(source_id, title, link, stated, retrieved):
    if not title:
        raise ValueError("no title")
    if not FEEDS[source_id]["site"].match(link):
        raise ValueError(f"not a link to the issuer's own site: {link[:80]!r}")
    published = parse_pub_date(stated)
    if published > retrieved:
        raise ValueError(f"stated as released at {published.isoformat()}, after this feed was read")
    return [link, title, stated, published.isoformat()]


def load_feed(conn, source_id, path, retrieved_at, raw_dir=None):
    """Keep one read of a central bank's feed and store its items. Returns a report dict."""
    if source_id not in FEEDS:
        raise EventFeedError(f"{source_id!r} is not a declared central-bank feed (ADR-010)")
    get_source(conn, source_id)
    path = Path(path)
    items = read_feed(path.read_bytes())
    retrieved = parse_timestamp(retrieved_at)

    def work(c):
        artifact_id, _ = store_raw_artifact(c, source_id, path, retrieved_at, raw_dir=raw_dir)
        new, present, problems, seen = [], 0, [], {}
        for number, (title, link, stated) in enumerate(items, 1):
            try:
                values = _parse_item(source_id, title, link, stated, retrieved)
            except ValueError as e:
                problems.append(("item_refused", f"item {number}: {e}"))
                continue
            if link not in seen:
                stored = c.execute("SELECT title, stated_time, published_at FROM me_items WHERE source_id = ?"
                                   " AND link = ?", [source_id, link]).fetchone()
                if stored:
                    seen[link] = list(stored)
            if link in seen:
                if seen[link] == values[1:]:
                    present += 1
                else:
                    problems.append(("item_conflict", f"item {number}: {link[:90]} was read before with a"
                                     " different title or time"))
                continue
            seen[link] = values[1:]
            new.append(values)
        earlier = c.execute("SELECT COUNT(*) FROM me_reads WHERE source_id = ?", [source_id]).fetchone()[0]
        overlaps = None if not earlier else int(present > 0)
        read_id = c.execute(
            "INSERT INTO me_reads (source_id, artifact_id, items, items_recorded, already_present, items_refused,"
            " overlaps_previous, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [source_id, artifact_id, len(items), len(new), present, len(problems), overlaps, now_utc()]).lastrowid
        c.executemany("INSERT INTO me_items (source_id, link, title, stated_time, published_at, read_id, recorded_at)"
                      " VALUES (?, ?, ?, ?, ?, ?, ?)", [[source_id] + v + [read_id, now_utc()] for v in new])
        c.executemany("INSERT INTO me_problems VALUES (?, ?, ?)", [(read_id, k, d) for k, d in problems])
        shown = [f"{k}: {d}" for k, d in problems[:PROBLEMS_SHOWN]]
        if len(problems) > PROBLEMS_SHOWN:
            shown.append(f"... and {len(problems) - PROBLEMS_SHOWN} more (table me_problems, read {read_id})")
        report = {"read_id": read_id, "items": len(items), "items_recorded": len(new), "already_present": present,
                  "items_refused": len(problems), "problems": shown}
        if overlaps == 0:
            report["warning"] = ("this read shares no item with the previous read of this feed - items published"
                                 " in between may have been missed (the feed keeps only its latest items)")
        return report

    return run_in_transaction(conn, work)


def _meeting(digits):
    """'260918' or '20260918' -> '2026-09-18', or None when it is not a real date."""
    text = digits if len(digits) == 8 else "20" + digits
    try:
        return strict_iso_date(f"{text[:4]}-{text[4:6]}-{text[6:]}").isoformat()
    except ValueError:
        return None


def classify(source_id, title, link):
    """Rule me-types-1: {kind, types, confidence, basis, meeting} for one stored feed item."""
    untyped = {"kind": "unclassified", "types": [], "confidence": ExtractionConfidence.NOT_TYPED,
               "basis": "no rule gives this item a registered type", "meeting": None}
    if source_id == "fed_monetary_feed":
        found = FED_RELEASE.match(link)
        if title == FED_DECISION_TITLE and found and _meeting(found[1]):
            return {"kind": "typed", "types": ["central_bank_decision"], "confidence": ExtractionConfidence.ISSUER_TITLE,
                    "basis": f"Fed title {FED_DECISION_TITLE!r}", "meeting": _meeting(found[1])}
        if FED_COMMUNICATION.match(title):
            return {**untyped, "kind": "communication", "basis": "Fed minutes or projections"}
        return untyped
    if source_id == "ecb_press_feed":
        found = ECB_CODE.match(link)
        if found and found[1] in ECB_DECISION_CODES and _meeting(found[2]):
            return {"kind": "typed", "types": ["central_bank_decision"],
                    "confidence": ExtractionConfidence.ISSUER_DOCUMENT_CODE,
                    "basis": f"ECB document code {found[1]!r}", "meeting": _meeting(found[2])}
        if found and found[1] in ECB_COMMUNICATION_CODES:
            return {**untyped, "kind": "communication", "basis": f"ECB document code {found[1]!r}"}
        return untyped
    if source_id == "boj_whatsnew_feed":
        found = BOJ_STATEMENT.match(link)
        if found and _meeting(found[1]):
            types, basis = ["central_bank_decision"], "BoJ statement file k" + found[1]
            if BOJ_RATE_CHANGE_TITLE in title:
                types, basis = types + ["policy_rate_change"], basis + f" titled {BOJ_RATE_CHANGE_TITLE!r}"
            return {"kind": "typed", "types": types, "confidence": ExtractionConfidence.ISSUER_DOCUMENT_CODE,
                    "basis": basis, "meeting": _meeting(found[1])}
        if BOJ_COMMUNICATION.match(link):
            return {**untyped, "kind": "communication", "basis": "BoJ minutes or summary of opinions"}
        return untyped
    raise EventFeedError(f"{source_id!r} is not a declared central-bank feed (ADR-010)")


def _rating(conn, source_id, cache):
    if source_id not in cache:
        cache[source_id] = get_source(conn, source_id)["reliability_rating"]
    return cache[source_id]


def _event(**fields):
    base = {"issuer": None, "links": [], "items": [], "period": None, "released_after": None, "dedup_rule": None,
            "direction": NOT_ASSESSED, "materiality": NOT_ASSESSED, "expected_horizon": NOT_ASSESSED,
            "surprise": NOT_ASSESSED}
    return {**base, **fields}


def _feed_events(conn, decision, claim, include_untyped, ratings):
    rows = conn.execute(
        "SELECT i.item_id, i.source_id, i.link, i.title, i.stated_time, i.published_at, a.retrieved_at"
        " FROM me_items i JOIN me_reads r ON r.read_id = i.read_id JOIN raw_artifacts a ON a.artifact_id = r.artifact_id"
        " ORDER BY i.published_at, i.item_id").fetchall()
    meetings, found = {}, []
    for item_id, source_id, link, title, stated, published, retrieved in rows:
        if disposition(claim, decision, retrieved, published) != Availability.ELIGIBLE:
            continue
        basis = retrieved if PitClaim(claim) == PitClaim.CURRENT_DECISION else published
        rule = classify(source_id, title, link)
        feed = FEEDS[source_id]
        if rule["kind"] == "typed":
            key = (source_id, rule["meeting"])
            if key in meetings:
                event = meetings[key]
                event["items"].append(item_id)
                event["links"].append(link)
                event["event_types"] = sorted(set(event["event_types"]) | set(rule["types"]))
                event["type_basis"] += "; " + rule["basis"]
                if parse_timestamp(basis) < parse_timestamp(event["available_at"]):
                    event["available_at"] = basis
                continue
            event = _event(
                event_id=f"{source_id}:{rule['meeting']}", source_id=source_id,
                group=GROUP_OF[rule["types"][0]], event_types=sorted(rule["types"]), kind="typed",
                region=feed["region"], institution=feed["institution"], title=title, links=[link], items=[item_id],
                stated=stated, happened_on=rule["meeting"], published_at=published, available_at=basis, claim=claim,
                extraction_confidence=rule["confidence"], type_basis=rule["basis"], type_rule=TYPES_RULE,
                dedup_rule=DEDUP_RULE, novelty="primary source",
                source_quality={"source": source_id, "reliability_rating": _rating(conn, source_id, ratings)})
            meetings[key] = event
            found.append(event)
        elif include_untyped:
            found.append(_event(
                event_id=f"{source_id}:item{item_id}", source_id=source_id, group=None, event_types=[],
                kind=rule["kind"], region=feed["region"], institution=feed["institution"], title=title, links=[link],
                items=[item_id], stated=stated, happened_on=parse_timestamp(published).date().isoformat(),
                published_at=published, available_at=basis, claim=claim, extraction_confidence=rule["confidence"],
                type_basis=rule["basis"], type_rule=TYPES_RULE, novelty="primary source",
                source_quality={"source": source_id, "reliability_rating": _rating(conn, source_id, ratings)}))
    return found


# ---- FRED's release calendar -------------------------------------------------------------------------

def calendar_request(release_id):
    """The parameters sent to FRED for one declared release (the key is added by the network module)."""
    if release_id not in CALENDAR_RELEASES:
        raise CalendarResponseError(f"release {release_id} is not declared in CALENDAR_RELEASES")
    return {"release_id": str(release_id), "include_release_dates_with_no_data": "true", "sort_order": "desc",
            "limit": str(CALENDAR_LIMIT)}


def read_release_dates(data, release_id):
    """The release dates in one FRED release/dates answer (bytes), sorted, or an exception."""
    try:
        answer = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise CalendarResponseError(f"FRED's calendar answer is not JSON: {e}") from None
    if not isinstance(answer, dict):
        raise CalendarResponseError("FRED's calendar answer is not a JSON object")
    if "error_code" in answer:
        raise CalendarResponseError(f"FRED refused: {str(answer.get('error_message'))[:200]}")
    missing = [k for k in CALENDAR_KEYS if k not in answer]
    if missing or not isinstance(answer["release_dates"], list):
        raise CalendarResponseError(f"Not a FRED release-dates answer: missing {missing or ['a list of dates']}")
    if not answer["release_dates"]:
        raise NoDataError(f"FRED listed no dates for release {release_id} - nothing is stored")
    dates = []
    for row in answer["release_dates"]:
        if not isinstance(row, dict) or set(row) != {"release_id", "date"} or row["release_id"] != release_id:
            raise CalendarResponseError(f"A row is not a date of release {release_id}: {str(row)[:80]}")
        try:
            dates.append(strict_iso_date(row["date"]).isoformat())
        except ValueError as e:
            raise CalendarResponseError(f"A row has a bad date: {e}") from None
    if len(set(dates)) != len(dates):
        raise CalendarResponseError(f"FRED listed a date twice for release {release_id}")
    return sorted(dates)


def load_release_dates(conn, release_id, path, retrieved_at, raw_dir=None):
    """Keep one read of FRED's calendar for one release; record its dates and any schedule change."""
    if release_id not in CALENDAR_RELEASES:
        raise CalendarResponseError(f"release {release_id} is not declared in CALENDAR_RELEASES")
    get_source(conn, CALENDAR_SOURCE)
    path = Path(path)
    dates = read_release_dates(path.read_bytes(), release_id)

    def work(c):
        artifact_id, _ = store_raw_artifact(c, CALENDAR_SOURCE, path, retrieved_at, raw_dir=raw_dir)
        before = c.execute("SELECT read_id FROM me_calendar_reads WHERE release_id = ? ORDER BY read_id DESC LIMIT 1",
                           [release_id]).fetchone()
        changes = []
        if before:
            old = [r[0] for r in c.execute("SELECT release_date FROM me_calendar_dates WHERE read_id = ?", [before[0]])]
            low, high = max(min(old), dates[0]), min(max(old), dates[-1])
            changes = ([("date_dropped", d) for d in sorted(set(old) - set(dates)) if low <= d <= high]
                       + [("date_added", d) for d in dates if d not in old and low <= d <= high])
        read_id = c.execute(
            "INSERT INTO me_calendar_reads (release_id, artifact_id, dates_listed, first_date, last_date, changes,"
            " recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [release_id, artifact_id, len(dates), dates[0], dates[-1], len(changes), now_utc()]).lastrowid
        c.executemany("INSERT INTO me_calendar_dates VALUES (?, ?)", [(read_id, d) for d in dates])
        c.executemany("INSERT INTO me_calendar_changes VALUES (?, ?, ?)", [(read_id, k, d) for k, d in changes])
        today = parse_timestamp(retrieved_at).date().isoformat()
        report = {"read_id": read_id, "release": CALENDAR_RELEASES[release_id][0], "dates_listed": len(dates),
                  "first": dates[0], "last": dates[-1], "upcoming": [d for d in dates if d >= today]}
        if changes:
            report["warning"] = "schedule changed since the previous read: " + ", ".join(f"{k} {d}" for k, d in changes)
        return report

    return run_in_transaction(conn, work)


def scheduled_releases(conn, decision_time, claim=PitClaim.CURRENT_DECISION, start=None, end=None):
    """The declared releases' dates as FRED's calendar showed them in the latest read known at decision_time.
    Under both claims a schedule is known from this system's read of it - FRED's calendar is not dated."""
    decision = parse_timestamp(decision_time)
    found = []
    for release_id, (name, region, series_id) in CALENDAR_RELEASES.items():
        latest = None
        for read_id, retrieved in conn.execute(
                "SELECT r.read_id, a.retrieved_at FROM me_calendar_reads r JOIN raw_artifacts a"
                " ON a.artifact_id = r.artifact_id WHERE r.release_id = ? ORDER BY a.retrieved_at, r.read_id",
                [release_id]):
            if disposition(claim, decision, retrieved, retrieved) == Availability.ELIGIBLE:
                latest = (read_id, retrieved)
        if latest is None:
            continue
        for (day,) in conn.execute("SELECT release_date FROM me_calendar_dates WHERE read_id = ? ORDER BY 1",
                                   [latest[0]]):
            if (start is None or day >= start) and (end is None or day <= end):
                found.append({"release_id": release_id, "release": name, "region": region, "series_id": series_id,
                              "date": day, "time_of_day": NOT_ASSESSED, "as_of": latest[1]})
    return sorted(found, key=lambda r: (r["date"], r["release_id"]))


# ---- events derived from stored data -------------------------------------------------------------

def _fred_release_events(conn, decision, claim, ratings):
    if not conn.execute("SELECT COUNT(*) FROM mc_series").fetchone()[0]:
        return []
    marks = ", ".join("?" for _ in FRED_RELEASE_SERIES)
    rows = conn.execute(
        "SELECT v.series_id, v.obs_date, v.realtime_start, v.start_clipped, v.available_at, a.retrieved_at, s.region"
        " FROM mc_vintages v JOIN mc_responses r ON r.response_id = v.response_id"
        " JOIN raw_artifacts a ON a.artifact_id = r.artifact_id JOIN mc_series s ON s.series_id = v.series_id"
        f" WHERE v.series_id IN ({marks}) AND v.value IS NOT NULL ORDER BY v.series_id, v.obs_date, v.realtime_start",
        list(FRED_RELEASE_SERIES)).fetchall()
    periods = {}
    for sid, day, start, clipped, available_at, retrieved, region in rows:
        if disposition(claim, decision, retrieved, available_at) != Availability.ELIGIBLE:
            continue
        basis = retrieved if PitClaim(claim) == PitClaim.CURRENT_DECISION else available_at
        known = periods.setdefault((sid, day), {"start": start, "clipped": clipped, "basis": basis, "region": region})
        if parse_timestamp(basis) < parse_timestamp(known["basis"]):
            known["basis"] = basis
    found = []
    for (sid, day), p in sorted(periods.items()):
        if p["clipped"]:
            continue   # the first release was before the stored real-time window: its date is not known
        found.append(_event(
            event_id=f"fred_alfred:{sid}:{day}", source_id="fred_alfred", group="sovereign_and_macro_data",
            event_types=["major_data_release"], kind="typed", region=p["region"], institution="FRED (ALFRED)",
            title=f"{FRED_RELEASE_SERIES[sid]} for the period starting {day}: first release", stated=p["start"],
            happened_on=p["start"], published_at=None, available_at=p["basis"], claim=claim, period=day,
            extraction_confidence=ExtractionConfidence.STATISTICS_RELEASE,
            type_basis=f"first vintage of {sid} for {day} (ALFRED real-time start {p['start']})",
            type_rule=RELEASES_RULE, novelty="derived from stored data", surprise=SURPRISE,
            source_quality={"source": "fred_alfred", "reliability_rating": _rating(conn, "fred_alfred", ratings)}))
    return found


def _mospi_release_events(conn, decision, claim, ratings):
    if not conn.execute("SELECT COUNT(*) FROM mo_series").fetchone()[0]:
        return []
    marks = ", ".join("?" for _ in MOSPI_RELEASE_SERIES)
    reads = {}
    for sid, read_id, read_at in conn.execute(
            "SELECT s.series_id, r.read_id, r.retrieved_at FROM mo_series s JOIN mo_reads r ON r.dataset = s.dataset"
            f" AND r.request = s.request WHERE s.series_id IN ({marks}) ORDER BY s.series_id, r.retrieved_at, r.read_id",
            list(MOSPI_RELEASE_SERIES)):
        if disposition(claim, decision, read_at, None) == Availability.ELIGIBLE:
            reads.setdefault(sid, []).append((read_id, read_at))   # historical replay: none (AVAILABILITY_REVIEW)
    first = {}
    for sid, period, read_id in conn.execute(
            f"SELECT series_id, period, read_id FROM mo_values WHERE series_id IN ({marks}) ORDER BY value_id",
            list(MOSPI_RELEASE_SERIES)):
        order = [r for r, _ in reads.get(sid, [])]
        if read_id in order and ((sid, period) not in first or order.index(read_id) < order.index(first[(sid, period)])):
            first[(sid, period)] = read_id
    found = []
    for (sid, period), read_id in sorted(first.items()):
        order = reads[sid]
        position = [r for r, _ in order].index(read_id)
        if position == 0:
            continue   # the history in the series' first read: when it was released is not known
        read_at, after = order[position][1], order[position - 1][1]
        found.append(_event(
            event_id=f"mospi_esankhyiki:{sid}:{period}", source_id="mospi_esankhyiki", group="sovereign_and_macro_data",
            event_types=["major_data_release"], kind="typed", region="India", institution="MoSPI",
            title=f"{MOSPI_RELEASE_SERIES[sid]} for the period starting {period}: new in this system's read",
            stated=None, released_after=after, happened_on=parse_timestamp(read_at).date().isoformat(), published_at=None,
            available_at=read_at, claim=claim, period=period, extraction_confidence=ExtractionConfidence.STATISTICS_RELEASE,
            type_basis=f"{sid} for {period} first read at {read_at[:16]} UTC, not in the read of {after[:16]} UTC"
                       " (MoSPI gives no release time)",
            type_rule=RELEASES_RULE, novelty="derived from stored data", surprise=SURPRISE,
            source_quality={"source": "mospi_esankhyiki", "reliability_rating": _rating(conn, "mospi_esankhyiki", ratings)}))
    return found


def _sebi_events(conn, decision, claim, ratings):
    if not conn.execute("SELECT COUNT(*) FROM sb_releases").fetchone()[0]:
        return []
    return [_event(
        event_id=f"sebi_rss:{r['release_id']}", source_id="sebi_rss", group="fiscal_trade_and_regulation",
        event_types=["sector_wide_regulation"], kind="typed", region="India", institution="SEBI", title=r["title"],
        links=[r["link"]], stated=r["stated_date"], happened_on=r["stated_date"], published_at=r["published_at"],
        available_at=r["published_at"], claim=claim, extraction_confidence=ExtractionConfidence.REGULATOR_SECTION,
        type_basis=f"SEBI section {r['section']}, no company named", type_rule=SEBI_RULE, novelty="primary source",
        source_quality={"source": "sebi_rss", "reliability_rating": _rating(conn, "sebi_rss", ratings)})
        for r in sebi_releases(conn, decision, claim) if r["section"] == "legal/circulars" and r["unassigned"]]


# ---- events declared by the owner ------------------------------------------------------------------

def _date_text(value, field):
    if isinstance(value, datetime):
        raise DeclaredEventError(f"{field} must be a date (YYYY-MM-DD), not a date and time")
    if isinstance(value, date):
        return value.isoformat()
    try:
        return strict_iso_date(value).isoformat()
    except ValueError as e:
        raise DeclaredEventError(f"{field}: {e}") from None


def _line(value, field, low, high):
    if not isinstance(value, str) or not low <= len(value.strip()) <= high or "\n" in value:
        raise DeclaredEventError(f"{field} must be one line of {low} to {high} characters")
    return value.strip()


def check_declared(entry, today):
    """One declared event as a canonical dict, or DeclaredEventError."""
    if not isinstance(entry, dict):
        raise DeclaredEventError(f"an entry is not a mapping: {str(entry)[:60]}")
    key = entry.get("event_key")
    unknown, missing = sorted(set(entry) - DECLARED_KEYS), sorted(DECLARED_REQUIRED - set(entry))
    if unknown or missing:
        raise DeclaredEventError(f"{key}: unknown fields {unknown}, missing fields {missing}")
    if not isinstance(key, str) or not EVENT_KEY.match(key):
        raise DeclaredEventError(f"{key!r}: event_key must be 3-61 lower-case letters, digits, - or _")
    kind = entry["event_type"]
    if kind in ISSUER_EVENT_TYPES:
        raise DeclaredEventError(f"{key}: {kind!r} is a company event type - it belongs to that company's filings")
    if kind not in MACRO_TYPES:
        raise DeclaredEventError(f"{key}: {kind!r} is not a registered macro event type (4A.0)")
    if entry["region"] not in REGIONS:
        raise DeclaredEventError(f"{key}: region must be one of {', '.join(REGIONS)}")
    occurred_on = _date_text(entry["occurred_on"], f"{key}: occurred_on")
    declared_on = _date_text(entry["declared_on"], f"{key}: declared_on")
    if not occurred_on <= declared_on <= today.isoformat():
        raise DeclaredEventError(f"{key}: dates must satisfy occurred_on <= declared_on <= today ({today})")
    occurred_at = entry.get("occurred_at")
    if occurred_at is not None:
        try:
            moment = parse_timestamp(occurred_at if isinstance(occurred_at, datetime) else str(occurred_at))
        except Exception:
            raise DeclaredEventError(f"{key}: occurred_at must be a time with its zone, e.g. 2026-12-04 10:00:00+05:30")
        if moment.date().isoformat() != occurred_on:
            raise DeclaredEventError(f"{key}: occurred_at is not on occurred_on")
        occurred_at = moment.isoformat()
    url = entry.get("source_url")
    if url is not None:
        if not isinstance(url, str) or not SOURCE_URL.match(url):
            raise DeclaredEventError(f"{key}: source_url must be a single https address")
        if RBI_URL.match(url):
            raise DeclaredEventError(f"{key}: RBI addresses are not stored - RBI's terms forbid linking without"
                                     " written permission (ADR-006); cite another public source")
    institution = entry.get("institution")
    return {"event_key": key, "event_group": GROUP_OF[kind], "event_type": kind, "region": entry["region"],
            "institution": None if institution is None else _line(institution, f"{key}: institution", 2, 80),
            "occurred_on": occurred_on, "occurred_at": occurred_at,
            "title": _line(entry["title"], f"{key}: title", 5, 160),
            "cited_source": _line(entry["source"], f"{key}: source", 3, 200), "source_url": url,
            "declared_on": declared_on}


DECLARED_COLUMNS = ("event_key", "event_group", "event_type", "region", "institution", "occurred_on", "occurred_at",
                    "title", "cited_source", "source_url", "declared_on")


def load_declared_file(path=DECLARED_FILE):
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict) or set(data) - {"events"} or not isinstance(data.get("events") or [], list):
        raise DeclaredEventError(f"{Path(path).name} must hold one list named 'events'")
    return data.get("events") or []


def sync_declared_events(conn, path=DECLARED_FILE, today=None):
    """Record new declared events. Every entry is checked before anything is written; a recorded event is
    never silently changed. Returns {"recorded": [...], "already_present": n, "not_in_file": [...]}."""
    today = today or datetime.now(timezone.utc).date()
    checked = [check_declared(e, today) for e in load_declared_file(path)]
    keys = [e["event_key"] for e in checked]
    if len(set(keys)) != len(keys):
        raise DeclaredEventError("an event_key is declared twice")
    stored = {r[0]: r[1] for r in conn.execute("SELECT event_key, entry FROM me_declared")}
    new = []
    for entry in checked:
        text = json.dumps(entry, sort_keys=True)
        if entry["event_key"] in stored:
            if stored[entry["event_key"]] != text:
                raise DeclaredEventError(f"{entry['event_key']} was recorded differently - recorded events are never"
                                         " silently changed; declare a correction under a new event_key")
            continue
        new.append(entry)

    def work(c):
        c.executemany(f"INSERT INTO me_declared ({', '.join(DECLARED_COLUMNS)}, entry, recorded_at)"
                      f" VALUES ({', '.join('?' for _ in DECLARED_COLUMNS)}, ?, ?)",
                      [[e[k] for k in DECLARED_COLUMNS] + [json.dumps(e, sort_keys=True), now_utc()] for e in new])

    run_in_transaction(conn, work)
    return {"recorded": [e["event_key"] for e in new], "already_present": len(checked) - len(new),
            "not_in_file": sorted(set(stored) - set(keys))}


def _declared_events(conn, decision, claim):
    found = []
    for row in conn.execute(f"SELECT {', '.join(DECLARED_COLUMNS)}, recorded_at FROM me_declared ORDER BY recorded_at"):
        e = dict(zip(DECLARED_COLUMNS + ("recorded_at",), row))
        if disposition(claim, decision, e["recorded_at"], None) != Availability.ELIGIBLE:
            continue   # under historical replay: no proven publication time (AVAILABILITY_REVIEW)
        found.append(_event(
            event_id=f"declared:{e['event_key']}", source_id=DECLARED_SOURCE, group=e["event_group"],
            event_types=[e["event_type"]], kind="typed", region=e["region"], institution=e["institution"],
            title=e["title"], links=[e["source_url"]] if e["source_url"] else [],
            stated=e["occurred_at"] or e["occurred_on"], happened_on=e["occurred_on"], published_at=None,
            available_at=e["recorded_at"], claim=claim, extraction_confidence=ExtractionConfidence.OWNER_DECLARED,
            type_basis=f"declared by the owner on {e['declared_on']}, citing {e['cited_source']}",
            type_rule=DECLARED_RULE, novelty="declared",
            source_quality={"source": DECLARED_SOURCE, "reliability_rating": NOT_ASSESSED}))
    return found


# ---- all events known at a decision time ------------------------------------------------------------

def macro_events(conn, decision_time, claim=PitClaim.CURRENT_DECISION, start=None, end=None, groups=None,
                 include_untyped=False):
    """Every macro event known at decision_time under the claim (5B.2), ordered by when it became known.
    start/end bound the day it happened; untyped feed items are left out unless asked for. No event has
    an issuer: attribution to a security goes through event_routes.attribute only."""
    decision = parse_timestamp(decision_time)
    claim = PitClaim(claim)
    ratings = {}
    found = (_feed_events(conn, decision, claim, include_untyped, ratings)
             + _fred_release_events(conn, decision, claim, ratings) + _mospi_release_events(conn, decision, claim, ratings)
             + _sebi_events(conn, decision, claim, ratings) + _declared_events(conn, decision, claim))
    found = [e for e in found if (start is None or e["happened_on"] >= start) and (end is None or e["happened_on"] <= end)
             and (groups is None or e["group"] in groups)]
    return sorted(found, key=lambda e: (parse_timestamp(e["available_at"]), e["event_id"]))


def release_dates_agree(conn, decision_time):
    """Cross-source check (4): for each derived US data release whose stated date falls inside the span of the
    latest calendar read known at decision_time, whether FRED's calendar lists that date too."""
    decision = parse_timestamp(decision_time)
    listed = {}
    for row in scheduled_releases(conn, decision):
        listed.setdefault(row["series_id"], set()).add(row["date"])
    checks = []
    for e in _fred_release_events(conn, decision, PitClaim.CURRENT_DECISION, {}):
        sid = e["event_id"].split(":")[1]
        days = listed.get(sid)
        if days and min(days) <= e["happened_on"] <= max(days):
            checks.append({"series_id": sid, "period": e["period"], "date": e["happened_on"],
                           "listed": e["happened_on"] in days})
    return checks


def check_registered_types():
    """Every macro event type is new to 4A.0's company groups, and every rule produces registered types."""
    produced = {"central_bank_decision", "policy_rate_change", "major_data_release", "sector_wide_regulation"}
    return not (MACRO_TYPES & ISSUER_EVENT_TYPES) and produced <= MACRO_TYPES
