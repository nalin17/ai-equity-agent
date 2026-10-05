"""Aggregate investor flows - NSE's daily FII/FPI and DII trading activity (architecture 40B step 9c, 3C rule 1,
3G, 4, 4C, 5B; ADR-011).

Input: the two CSV files of NSE's page 'FII/FPI & DII trading activity' (nseindia.com/reports/fii-dii),
downloaded by a person each trading evening (ADR-004): fii-dii-nse-latest.csv (NSE) and
fii-dii-combined-latest.csv (NSE, BSE and MSEI). NSDL's and CDSL's final FPI figures are not used: their terms
forbid storing them without written permission (ADR-011; permission was requested).

Rules, each found on NSE's real files for 01-Oct-2026 (downloaded 04-Oct-2026):
  - The page and each file hold only the latest trading day: a header and two rows, DII and FII/FPI, with buy,
    sell and net value in Rs crore. The file names carry no date and repeat every day (the intake keeps a newer
    download beside the old one under a content tag). A day not downloaded on the day cannot be recovered from
    the page: such trading days are reported as missing (extraction failure), never filled.
  - Header cells are split over two lines and carry the rupee sign; the file starts with a byte-order mark. The
    header must be exactly the declared five columns in crore - anything else refuses the file whole (a changed
    format is fixed here, never by loosening the check, 4G rule 7).
  - Numbers carry thousands commas and a minus sign ('-9,484.22'). Buy and sell are never negative and net must
    equal buy minus sell to the paisa; both categories must be present once, for the same day. Any break
    refuses the file whole - nothing is repaired (4).
  - The trade date must be an NSE trading day by the declared calendar (XBOM) and not after the file was
    ingested (India date). Outside the calendar's coverage the file is refused - never guessed.
  - Availability (3C rule 1, 5B): the file gives no publication time, so a value is known from this system's
    ingestion of the file - later than the truth, never earlier, and never its trade date. Under historical
    replay nothing is returned (AVAILABILITY_REVIEW).
  - NSE marks the figures provisional. The same day read again with different figures is a new vintage and
    counted as revised; the earlier vintage stays known as of earlier.
  - Flows are context (3G rule 2): never a covered security, a target or a benchmark.
"""
import re
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from core.calendars import CalendarError, load_calendars
from core.dates import strict_iso_date
from core.database import now_utc, run_in_transaction
from data_quality.missing_data import MissingClass
from data_quality.trust_chain import NoDataError
from ingestion.market_adapters import AdapterError, read_raw_table
from ingestion.nse_financial_results import IST
from ingestion.source_registry import get_source
from provenance.availability import Availability, disposition, parse_timestamp
from provenance.raw_store import store_raw_artifact

SOURCE_ID = "nse_fii_dii"
CALENDAR = "XBOM"
RUPEE = chr(0x20B9)
FILE_SCOPES = (   # file name -> scope; the content tag is added by the intake when a name repeats
    (re.compile(r"^fii-dii-nse-latest(__[0-9a-f]{8})?\.csv$"), "nse"),
    (re.compile(r"^fii-dii-combined-latest(__[0-9a-f]{8})?\.csv$"), "nse_bse_msei"),
)
SCOPE_TITLES = {"nse": "NSE", "nse_bse_msei": "NSE, BSE and MSEI"}
HEADER = ("CATEGORY", "DATE", f"BUY VALUE ({RUPEE} Crores)", f"SELL VALUE ({RUPEE} Crores)",
          f"NET VALUE ({RUPEE} Crores)")
CATEGORIES = ("FII/FPI", "DII")
DATE_FORMAT = "%d-%b-%Y"                                   # e.g. 01-Oct-2026
AMOUNT = re.compile(r"^-?(\d{1,3}(,\d{3})*|\d{1,2}(,\d{2})*,\d{3})\.\d{2}$")   # 25,420.04 or 1,25,420.04
STATUS = "provisional"
UNIT = "INR crore"


class FlowsFileError(AdapterError):
    """The file cannot be used as a whole. Nothing is stored."""


def scope_of(name):
    """'nse' or 'nse_bse_msei' for a recognised file name, else None."""
    return next((scope for pattern, scope in FILE_SCOPES if pattern.match(name)), None)


def _amount(text, what):
    text = (text or "").strip()
    if not AMOUNT.match(text):
        raise FlowsFileError(f"{what} {text[:20]!r} is not an amount like 25,420.04")
    return Decimal(text.replace(",", ""))


def _trading_day(day):
    calendars, _ = load_calendars()
    cal = calendars[CALENDAR]
    try:
        traded = cal.is_session(day)
    except CalendarError:
        raise FlowsFileError(f"the NSE calendar does not cover {day} - regenerate the calendars (ADR-009)") from None
    if not traded:
        raise FlowsFileError(f"{day} was not an NSE trading day")


def read_flows(path, retrieved):
    """(scope, trade date, {category: (buy, sell, net, text)}) of one file, or an exception. Nothing is stored."""
    path = Path(path)
    scope = scope_of(path.name)
    if scope is None:
        raise FlowsFileError(f"{path.name} is not an NSE FII/DII file name")
    header, rows = read_raw_table(path)
    if tuple(" ".join(h.split()) for h in header) != HEADER:
        raise FlowsFileError(f"{path.name}: not NSE's FII/DII table in crore - header {[' '.join(h.split()) for h in header]}")
    if not rows:
        raise NoDataError(f"{path.name}: no rows - nothing is stored")
    if len(rows) != len(CATEGORIES):
        raise FlowsFileError(f"{path.name}: {len(rows)} rows, not one each for {', '.join(CATEGORIES)}")
    found, days = {}, set()
    for row_number, row in rows:
        values = [row.get(h, "") for h in header]
        category = values[0].strip()
        if category not in CATEGORIES or category in found:
            raise FlowsFileError(f"{path.name} row {row_number}: category {category[:20]!r} unknown or repeated")
        try:
            days.add(datetime.strptime(values[1].strip(), DATE_FORMAT).date())
        except ValueError:
            raise FlowsFileError(f"{path.name} row {row_number}: date {values[1][:20]!r} is not like 01-Oct-2026") from None
        buy, sell, net = (_amount(values[i], f"row {row_number} {HEADER[i].split()[0].lower()}") for i in (2, 3, 4))
        if buy < 0 or sell < 0:
            raise FlowsFileError(f"{path.name} row {row_number}: a buy or sell value is negative")
        if net != buy - sell:
            raise FlowsFileError(f"{path.name} row {row_number}: net {net} is not buy {buy} minus sell {sell}")
        found[category] = (buy, sell, net, " | ".join(v.strip() for v in values[2:5]))
    if len(days) != 1:
        raise FlowsFileError(f"{path.name}: the rows are for different days {sorted(str(d) for d in days)}")
    day = days.pop()
    if day > parse_timestamp(retrieved).astimezone(IST).date():
        raise FlowsFileError(f"{path.name}: trade date {day} is after the file was ingested")
    _trading_day(day)
    return scope, day.isoformat(), found


def load_flows(conn, path, retrieved_at, raw_dir=None):
    """Keep one NSE FII/DII file and store its figures as vintages. Returns a report dict."""
    get_source(conn, SOURCE_ID)
    scope, day, found = read_flows(path, retrieved_at)

    def work(c):
        artifact_id, _ = store_raw_artifact(c, SOURCE_ID, Path(path), retrieved_at, raw_dir=raw_dir)
        new, present, revised = [], 0, 0
        for category in CATEGORIES:
            buy, sell, net, text = found[category]
            known = c.execute("SELECT value_text FROM fl_flows WHERE scope = ? AND trade_date = ? AND category = ?"
                              " ORDER BY flow_id DESC LIMIT 1", [scope, day, category]).fetchone()
            if known and known[0] == text:
                present += 1
                continue
            revised += int(known is not None)
            new.append([scope, day, category, float(buy), float(sell), float(net), text])
        file_id = c.execute("INSERT INTO fl_files (artifact_id, scope, trade_date, recorded, revised, recorded_at)"
                            " VALUES (?, ?, ?, ?, ?, ?)", [artifact_id, scope, day, len(new), revised, now_utc()]).lastrowid
        c.executemany("INSERT INTO fl_flows (scope, trade_date, category, buy_crore, sell_crore, net_crore, value_text,"
                      " file_id, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      [v + [file_id, now_utc()] for v in new])
        return {"file_id": file_id, "scope": scope, "trade_date": day, "values_recorded": len(new),
                "already_present": present, "revised": revised,
                "fii_fpi_net_crore": str(found["FII/FPI"][2]), "dii_net_crore": str(found["DII"][2])}

    return run_in_transaction(conn, work)


def flows(conn, decision_time, claim, scope="nse", start=None, end=None):
    """The flows known at decision_time under the claim, oldest trading day first: for each day and category the
    latest vintage ingested by then. Under historical replay nothing is returned - NSE gives no publication time
    (AVAILABILITY_REVIEW, 3C rule 1)."""
    known = {}
    for day, category, buy, sell, net, text, retrieved in conn.execute(
            "SELECT f.trade_date, f.category, f.buy_crore, f.sell_crore, f.net_crore, f.value_text, a.retrieved_at"
            " FROM fl_flows f JOIN fl_files x ON x.file_id = f.file_id JOIN raw_artifacts a ON a.artifact_id = x.artifact_id"
            " WHERE f.scope = ? ORDER BY f.flow_id", [scope]):
        if disposition(claim, decision_time, retrieved, None) != Availability.ELIGIBLE:
            continue
        if (start is None or day >= start) and (end is None or day <= end):
            known[(day, category)] = {"scope": scope, "trade_date": day, "category": category, "buy_crore": buy,
                                      "sell_crore": sell, "net_crore": net, "value_text": text, "known_from": retrieved,
                                      "status": STATUS, "unit": UNIT}
    return [known[k] for k in sorted(known)]


def missing_days(conn, decision_time, claim, scope, start, end):
    """NSE trading days in [start, end] with no file ingested by decision_time: each with its missing-data class.
    NSE's page shows only the latest day, so a day not downloaded on the day is lost - never filled (4C)."""
    have = {r["trade_date"] for r in flows(conn, decision_time, claim, scope, start, end)}
    calendars, _ = load_calendars()
    cal = calendars[CALENDAR]
    day, last, found = strict_iso_date(start), strict_iso_date(end), []
    while day <= last:
        try:
            traded = cal.is_session(day)
        except CalendarError:
            break   # beyond the calendar's coverage nothing is claimed
        if traded and day.isoformat() not in have:
            found.append({"trade_date": day.isoformat(), "missing_class": MissingClass.EXTRACTION_FAILURE,
                          "reason": "no file for this trading day - NSE's page shows only the latest day"})
        day += timedelta(days=1)
    return found
