"""Stage 10C-2 tests: market calendars and India macro context from MoSPI (architecture 40B step 9a, 3G, 4C.1,
4G, 5A.1, 5B, 5C rule 4; ADR-009).

Built on real data of 03/04-Oct-2026: NSE's official 2026 trading-holiday list; FRED showing the Nasdaq on
Good Friday 19-Apr-2019 and the Nikkei on 1-Oct-2020 (the Tokyo exchange's outage), each the previous close
repeated - the dates are real, the index values here are made up; and MoSPI's answers - CPI base 2024 All
India (August 2026 index 108.74, inflation 4.82), the CPI back series (December 2024 index 102.90, inflation
5.22), IIP base 2022-23 (August 2026 general index 123.3, growth 8.0; manufacturing 126.6 among sub-industry
rows) and quarterly GDP (April-June 2026: 8136153 crore at constant prices, 8826871 at current prices).
MoSPI figures are used with attribution - Source: MoSPI, National Statistics Office, eSankhyiki (GSDD 2026
Category A). Other MoSPI values here are made up.
"""
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from core import calendars as market_calendars
from core.calendars import CalendarError, check_calendar, load_calendars
from core.config import PROJECT_ROOT
from core.database import connect, migrate, rollback
from data_quality.missing_data import MissingClass
from data_quality.trust_chain import NoDataError
from ingestion import macro_context, news_fetch
from ingestion.india_macro import (ATTRIBUTION, IndiaSeriesError, MospiResponseError, check_entry, india_latest,
                                   india_observations, load_mospi_pages, load_series_file, period_of, read_page,
                                   requests_to_fetch, sync_india_series)
from ingestion.macro_context import MacroSeriesError, load_fred_answers, series_info, sync_series, value_on
from ingestion.source_registry import get_source, sync_sources
from provenance.availability import PitClaim
from provenance.raw_store import ArtifactError

UTC = timezone.utc
REPLAY = PitClaim.HISTORICAL_REPLAY
READ = datetime(2026, 10, 3, 14, 39, tzinfo=UTC)
WINDOW = "2023-10-04"                                 # FRED's rolling real-time window on READ
RUPEE = chr(0x20B9)
NSE_2026_HOLIDAYS = ["2026-01-15", "2026-01-26", "2026-03-03", "2026-03-26", "2026-03-31", "2026-04-03",
                     "2026-04-14", "2026-05-01", "2026-05-28", "2026-06-26", "2026-09-14", "2026-10-02",
                     "2026-10-20", "2026-11-10", "2026-11-24", "2026-12-25"]   # NSE's official list


def at(text):
    return datetime.fromisoformat(text)


# ---- market calendars (core/calendars.py) ------------------------------------------------------

def test_the_calendar_file_is_complete():
    calendars, mapping = load_calendars()
    assert sorted(calendars) == ["XBOM", "XNYS", "XTKS"]
    for cal in calendars.values():
        assert (cal.coverage_from.isoformat(), cal.coverage_to.isoformat()) == ("2006-01-01", "2026-12-31")
    assert {c: len(cal.closed_weekdays) for c, cal in calendars.items()} == {"XNYS": 197, "XTKS": 342, "XBOM": 306}
    assert mapping == {"NASDAQCOM": "XNYS", "NIKKEI225": "XTKS"}


def test_the_india_calendar_agrees_with_nse_official_2026_holidays():
    calendars, _ = load_calendars()
    assert sorted(d.isoformat() for d in calendars["XBOM"].closed_weekdays if d.year == 2026) == NSE_2026_HOLIDAYS


@pytest.mark.parametrize("cid, day, traded", [
    ("XNYS", "2019-04-19", False),   # Good Friday - FRED shows the previous Nasdaq close repeated
    ("XNYS", "2019-04-18", True),
    ("XNYS", "2025-01-09", False),   # national day of mourning
    ("XNYS", "2012-10-29", False),   # hurricane Sandy
    ("XNYS", "2012-10-30", False),
    ("XNYS", "2019-04-20", False),   # a Saturday
    ("XTKS", "2020-10-01", False),   # the Tokyo exchange's all-day outage - FRED shows the previous close
    ("XTKS", "2020-10-02", True),
    ("XTKS", "2026-12-31", False),
    ("XBOM", "2024-01-20", True),    # a Saturday special session
    ("XBOM", "2025-02-01", True),    # Budget day, a Saturday
    ("XBOM", "2025-02-02", False),
    ("XBOM", "2026-10-02", False),   # Gandhi Jayanti
    ("XBOM", "2026-08-20", True), ("XBOM", "2026-08-21", True), ("XBOM", "2026-09-21", True),
    ("XBOM", "2026-09-22", True), ("XBOM", "2026-09-30", True), ("XBOM", "2026-10-01", True),   # the owner's bhavcopies
])
def test_calendars_know_real_trading_days(cid, day, traded):
    calendars, _ = load_calendars()
    assert calendars[cid].is_session(day) is traded


@pytest.mark.parametrize("day", ["2005-12-30", "2027-01-04"])
def test_a_calendar_knows_nothing_outside_its_coverage(day):
    calendars, _ = load_calendars()
    with pytest.raises(CalendarError, match="covers 2006-01-01 to 2026-12-31"):
        calendars["XNYS"].is_session(day)


GOOD_CAL = {"calendar_id": "XABC", "name": "Test", "time_zone": "Asia/Tokyo", "coverage_from": "2026-01-01",
            "coverage_to": "2026-12-31", "closed_weekdays": ["2026-01-01", "2026-01-02"], "weekend_sessions": ["2026-01-03"]}


@pytest.mark.parametrize("change, message", [
    ({"closed_weekdays": ["2026-01-03"]}, "only hold Monday-Friday"),
    ({"weekend_sessions": ["2026-01-05"]}, "only hold Saturday or Sunday"),
    ({"closed_weekdays": ["2026-01-02", "2026-01-01"]}, "sorted without repeats"),
    ({"closed_weekdays": ["2026-01-01", "2026-01-01"]}, "sorted without repeats"),
    ({"closed_weekdays": ["2027-01-01"]}, "outside the coverage"),
    ({"closed_weekdays": ["2026-1-1"]}, "YYYY-MM-DD"),
    ({"closed_weekdays": "2026-01-01"}, "must be a list"),
    ({"time_zone": "Europe/London"}, "not declared in core/sessions.py"),
    ({"calendar_id": "xabc"}, "not a calendar id"),
    ({"coverage_from": "2027-01-01"}, "coverage_from is after coverage_to"),
    ({"coverage_to": "31-12-2026"}, "coverage"),
    ({"name": None, "extra": 1}, "needs exactly"),
])
def test_a_calendar_declared_wrongly_is_refused(change, message):
    entry = {**GOOD_CAL, **change}
    if "extra" in change:
        entry.pop("name")
    with pytest.raises(CalendarError, match=message):
        check_calendar(entry)


def test_a_calendar_file_must_hang_together(tmp_path):
    good = ("calendars:\n  - {calendar_id: XABC, name: Test, time_zone: Asia/Tokyo, coverage_from: '2026-01-01',"
            " coverage_to: '2026-12-31', closed_weekdays: [], weekend_sessions: []}\n")
    for text, message in ((good + "series_calendars: {NIKKEI225: XNOPE}\n", "unknown calendar"),
                          (good.replace("calendars:\n", "calendars:\n") + good.split("\n", 1)[1]
                           + "series_calendars: {}\n", "declared twice"),
                          (good, "needs exactly 'calendars' and 'series_calendars'")):
        path = tmp_path / f"cal_{len(text)}.yaml"
        path.write_text(text, encoding="ascii")
        with pytest.raises(CalendarError, match=message):
            load_calendars(path)
    path = tmp_path / "ok.yaml"
    path.write_text(good + "series_calendars: {NIKKEI225: XABC}\n", encoding="ascii")
    calendars, mapping = load_calendars(path)
    assert calendars["XABC"].is_session("2026-01-05") and mapping == {"NIKKEI225": "XABC"}


# ---- a market's calendar decides its closes (5C rule 4) --------------------------------------------

def fred_rows(spec):
    return [{"realtime_start": s[2], "realtime_end": "9999-12-31", "date": s[0], "value": s[1]} for s in spec]


@pytest.fixture
def env(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    sync_series(c)
    sync_india_series(c)
    files = iter(range(1000))

    def fred(sid, spec, updated="2026-10-02 22:38:54-05"):
        info = series_info(c, sid)
        asked = {"series_id": sid, "observation_start": info["history_from"], "realtime_start": WINDOW,
                 "realtime_end": "9999-12-31"}
        doc = {"realtime_start": WINDOW, "realtime_end": "9999-12-31", "observation_start": info["history_from"],
               "units": "lin", "output_type": 1, "count": len(spec), "offset": 0, "observations": fred_rows(spec)}
        meta = {"seriess": [{"id": sid, "units": info["fred_units"], "frequency_short": "D", "last_updated": updated}]}
        n = next(files)
        (tmp_path / f"o{n}.json").write_text(json.dumps(doc), encoding="ascii")
        (tmp_path / f"m{n}.json").write_text(json.dumps(meta), encoding="ascii")
        return load_fred_answers(c, sid, tmp_path / f"o{n}.json", READ, tmp_path / f"m{n}.json",
                                 READ + timedelta(seconds=2), asked, raw_dir=tmp_path / "raw")

    def mospi(dataset, request, *bodies, read=READ):
        pages = []
        for number, body in enumerate(bodies, 1):
            path = tmp_path / f"p{next(files)}.json"
            path.write_bytes(body)
            pages.append((path, read + timedelta(seconds=number)))
        return load_mospi_pages(c, dataset, request, pages, raw_dir=tmp_path / "raw")

    yield c, fred, mospi, tmp_path
    c.close()


NASDAQ = [("2019-04-18", "1000.5", WINDOW), ("2019-04-19", "1000.5", WINDOW), ("2019-04-22", "1010.25", WINDOW),
          ("2019-04-26", ".", WINDOW)]
AFTER = READ + timedelta(hours=1)


def test_a_value_on_a_day_the_market_was_closed_is_never_used(env):
    c, fred, _, _ = env
    fred("NASDAQCOM", NASDAQ)
    found = value_on(c, "NASDAQCOM", "2019-04-19", AFTER)
    assert found["value"] is None and found["missing_class"] == MissingClass.STRUCTURALLY_ABSENT
    assert "XNYS was closed" in found["reason"] and "not a session close" in found["reason"]
    assert value_on(c, "NASDAQCOM", "2019-04-18", AFTER)["value"] == 1000.5
    assert c.execute("SELECT value FROM mc_vintages WHERE obs_date = '2019-04-19'").fetchone() == (1000.5,)   # kept as given


def test_the_nikkei_on_the_tokyo_outage_day_is_never_used(env):
    c, fred, _, _ = env
    fred("NIKKEI225", [("2020-09-30", "100.5", WINDOW), ("2020-10-01", "100.5", WINDOW), ("2020-10-02", "99.0", WINDOW)],
         updated="2026-10-02 07:02:36-05")
    assert value_on(c, "NIKKEI225", "2020-10-01", AFTER)["missing_class"] == MissingClass.STRUCTURALLY_ABSENT
    assert [r["date"] for r in macro_context.observations(c, "NIKKEI225", AFTER) if r["value"] is not None] == \
        ["2020-09-30", "2020-10-02"]


def test_no_value_on_a_trading_day_is_a_conflict_between_the_sources(env):
    c, fred, _, _ = env
    fred("NASDAQCOM", NASDAQ)
    found = value_on(c, "NASDAQCOM", "2019-04-26", AFTER)
    assert found["missing_class"] == MissingClass.SOURCE_CONFLICT and "XNYS traded" in found["reason"]


@pytest.mark.parametrize("day, wanted, reason", [
    ("2019-04-20", MissingClass.STRUCTURALLY_ABSENT, "XNYS was closed"),          # Saturday
    ("2019-04-23", MissingClass.EXTRACTION_FAILURE, "XNYS traded but no row"),
    ("2026-10-05", MissingClass.NOT_YET_RELEASED, "not published"),
    ("2005-12-30", MissingClass.EXTRACTION_FAILURE, "before the stored history"),  # outside the calendar
])
def test_dates_without_a_row_are_classified_by_the_calendar(env, day, wanted, reason):
    c, fred, _, _ = env
    fred("NASDAQCOM", NASDAQ)
    found = value_on(c, "NASDAQCOM", day, AFTER)
    assert found["value"] is None and found["missing_class"] == wanted and reason in found["reason"]


def test_the_latest_close_skips_a_closed_day(env):
    c, fred, _, _ = env
    fred("NASDAQCOM", NASDAQ[:2])
    found = macro_context.latest(c, "NASDAQCOM", AFTER)
    assert found["date"] == "2019-04-18" and found["later_dates_without_value"] == ["2019-04-19"]


def test_a_series_without_a_calendar_keeps_its_own_listing(env):
    # Cboe computes VIX on some US holidays (real: Memorial Day 2022); FRED's listing stays its authority.
    c, fred, _, _ = env
    fred("VIXCLS", [("2022-05-30", "26.5", WINDOW)], updated="2026-10-02 08:37:32-05")
    assert value_on(c, "VIXCLS", "2022-05-30", AFTER)["value"] == 26.5


def test_rows_outside_a_calendars_coverage_keep_freds_listing(env, monkeypatch):
    c, fred, _, _ = env
    narrow = check_calendar({**GOOD_CAL, "calendar_id": "XNYS", "time_zone": "America/New_York",
                             "coverage_from": "2019-04-18", "coverage_to": "2019-04-19", "closed_weekdays": ["2019-04-19"],
                             "weekend_sessions": []})
    monkeypatch.setattr(macro_context, "load_calendars", lambda *a: ({"XNYS": narrow}, {"NASDAQCOM": "XNYS"}))
    fred("NASDAQCOM", NASDAQ)
    assert value_on(c, "NASDAQCOM", "2019-04-19", AFTER)["missing_class"] == MissingClass.STRUCTURALLY_ABSENT
    assert value_on(c, "NASDAQCOM", "2019-04-22", AFTER)["value"] == 1010.25        # outside: as FRED gave it
    assert value_on(c, "NASDAQCOM", "2019-04-26", AFTER)["missing_class"] == MissingClass.STRUCTURALLY_ABSENT


def test_a_calendar_mapped_to_the_wrong_kind_of_series_is_refused(env, monkeypatch):
    c, fred, _, _ = env
    calendars, _ = load_calendars()
    monkeypatch.setattr(macro_context, "load_calendars", lambda *a: (calendars, {"DGS10": "XNYS"}))
    with pytest.raises(MacroSeriesError, match="not a market close"):
        value_on(c, "DGS10", "2026-09-30", AFTER)


# ---- the India series registry --------------------------------------------------------------------

def test_every_india_series_is_valid_and_recorded(env):
    c, *_ = env
    declared = load_series_file()
    assert len(declared) == 9 and c.execute("SELECT COUNT(*) FROM mo_series").fetchone()[0] == 9
    assert {e["series_id"] for e in declared if e["status"] == "reconstructed"} == {"IN_CPI24B_GEN_INDEX",
                                                                                    "IN_CPI24B_GEN_INFL"}
    assert [d for d, _ in requests_to_fetch(c)] == ["cpi", "cpi", "iip", "iip", "nas"]
    assert sync_india_series(c) == []


GOOD = {"series_id": "IN_TEST_INDEX", "title": "Test", "group": "economic_releases", "dataset": "cpi",
        "request": {"base_year": "2024", "series": "Current"}, "expect": {"base_year": "2024"}, "select": {},
        "measure": "index", "unit": "index", "status": "published", "publisher": "MoSPI", "licence": "GSDD"}


@pytest.mark.parametrize("change, message", [
    ({"series_id": "CPI_TEST"}, "not a series id"),
    ({"dataset": "wpi"}, "dataset"),
    ({"measure": "growth_rate"}, "measure"),
    ({"group": "flows"}, "group"),
    ({"status": "final"}, "status"),
    ({"status": "reconstructed"}, "only a back series"),
    ({"request": {"series": "Back"}}, "must be declared reconstructed"),
    ({"request": {"base_year": "2024", "limit": "100"}}, "paging is added by the fetcher"),
    ({"request": {}}, "request must map"),
    ({"expect": {}}, "expect must map"),
    ({"select": {"base_year": "2024"}}, "both expected and selected"),
    ({"select": ["group"]}, "select must map"),
    ({"title": " "}, "title must be text"),
    ({"colour": "red"}, "unknown fields"),
])
def test_an_india_series_declared_wrongly_is_refused(change, message):
    with pytest.raises(IndiaSeriesError, match=message):
        check_entry({**GOOD, **change})


def test_recorded_india_series_are_never_silently_changed(env, tmp_path):
    c, *_ = env
    text = (PROJECT_ROOT / "config" / "india_macro_series.yaml").read_text(encoding="ascii")
    for changed, message in ((text.replace("unit: INR crore, current prices", "unit: INR lakh"), "never silently changed"),
                             (text.replace("series_id: IN_GDP2223_Q_NOMINAL", "series_id: IN_GDP2223_Q_NOM"),
                              "no longer declared"),
                             (text.replace("series_id: IN_GDP2223_Q_NOMINAL", "series_id: IN_GDP2223_Q_REAL"),
                              "declared twice")):
        path = tmp_path / f"s{len(changed)}.yaml"
        path.write_text(changed, encoding="ascii")
        with pytest.raises(IndiaSeriesError, match=message):
            sync_india_series(c, path)


def test_series_sharing_a_request_must_expect_the_same_fields(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    text = (PROJECT_ROOT / "config" / "india_macro_series.yaml").read_text(encoding="ascii")
    first = text.index("expect: {base_year: \"2022-23\", type: General")
    path = tmp_path / "x.yaml"
    path.write_text(text[:first] + text[first:].replace("category: General}", "category: Other}", 1), encoding="ascii")
    with pytest.raises(IndiaSeriesError, match="must expect the same fields"):
        sync_india_series(c, path)
    c.close()


# ---- MoSPI answers -------------------------------------------------------------------------------

def page(rows, number=1, total=None, pages=1, status=True):
    return json.dumps({"data": rows, "meta_data": {"page": number, "totalRecords": len(rows) if total is None else total,
                       "totalPages": pages, "recordPerPage": 100}, "msg": "Data fetched successfully",
                       "statusCode": status}).encode()


def cpi(year, month, index, inflation, series="Current", sector="Combined", group=None):
    return {"base_year": "2024", "series": series, "year": str(year), "month": month, "state": "All India",
            "sector": sector, "division": "CPI (General)", "group": group, "class": None, "sub_class": None,
            "item": None, "code": None, "index": index, "inflation": inflation, "imputation": None}


def iip(month, index, growth, type_="General", category="General", sub=""):
    return {"base_year": "2022-23", "year": 2026, "month": month, "type": type_, "category": category,
            "sub_category": sub, "index": index, "growth_rate": growth}


def gdp(year, quarter, real, nominal):
    return {"base_year": "2022-23", "series": "Current", "year": year, "indicator": "Gross Domestic Product",
            "frequency": "Quarterly", "revision": None, "quarter": quarter, "current_price": nominal,
            "constant_price": real, "unit": RUPEE + " Crore"}


def request(c, dataset, **match):
    return next(r for d, r in requests_to_fetch(c) if d == dataset and all(r.get(k) == v for k, v in match.items()))


CPI_ROWS = [cpi(2026, "August", "108.74", "4.82"), cpi(2025, "January", "100.10", None)]


def value(c, sid, period, when=AFTER):
    found = [r for r in india_observations(c, sid, when) if r["period"] == period]
    return found[0]["value"] if found else None


def test_one_read_serves_every_series_asking_the_same_request(env):
    c, _, mospi, _ = env
    report = mospi("cpi", request(c, "cpi", series="Current"), page(CPI_ROWS))
    assert report["series"] == ["IN_CPI24_GEN_INDEX", "IN_CPI24_GEN_INFL"]
    assert (report["rows"], report["values_recorded"], report["values_not_given"], report["rows_refused"]) == (2, 3, 1, 0)
    assert value(c, "IN_CPI24_GEN_INDEX", "2026-08-01") == 108.74 and value(c, "IN_CPI24_GEN_INFL", "2026-08-01") == 4.82
    assert value(c, "IN_CPI24_GEN_INFL", "2025-01-01") is None   # MoSPI gives no rate for a base's first year


def test_the_aggregate_row_is_picked_from_breakdown_rows(env):
    c, _, mospi, _ = env
    rows = [iip("August", "126.6", "4.0", "Sectoral", "Manufacturing"),
            iip("August", "104.5", "2.8", "Sectoral", "Manufacturing", "Manufacture of Food Products"),
            iip("August", "120.5", "18.3", "Sectoral", "Manufacturing", "Manufacture of Beverages")]
    report = mospi("iip", request(c, "iip", category_code="2"), page(rows))
    assert (report["values_recorded"], report["rows_refused"]) == (1, 0)
    assert value(c, "IN_IIP2223_MFG_INDEX", "2026-08-01") == 126.6


def test_an_answer_without_the_declared_aggregate_says_so(env):
    c, _, mospi, _ = env
    rows = [iip("August", "104.5", "2.8", "Sectoral", "Manufacturing", "Manufacture of Food Products")]
    report = mospi("iip", request(c, "iip", category_code="2"), page(rows))
    assert report["values_recorded"] == 0 and report["problems"][0].startswith("no_aggregate_row")


def test_gdp_quarters_are_financial_year_quarters(env):
    c, _, mospi, _ = env
    rows = [gdp("2026-27", "Q1", "8136153", "8826871"), gdp("2025-26", "Q4", "8000000", "8700000")]
    mospi("nas", request(c, "nas"), page(rows))
    assert value(c, "IN_GDP2223_Q_REAL", "2026-04-01") == 8136153 and value(c, "IN_GDP2223_Q_NOMINAL", "2026-04-01") == 8826871
    assert value(c, "IN_GDP2223_Q_REAL", "2026-01-01") == 8000000


@pytest.mark.parametrize("row, message", [
    ({"year": "2026-28", "quarter": "Q1"}, "not two consecutive years"),
    ({"year": "2026", "quarter": "Q1"}, "not a financial-year quarter"),
    ({"year": "2026-27", "quarter": "Q5"}, "not a financial-year quarter"),
])
def test_bad_quarters_are_refused(row, message):
    with pytest.raises(ValueError, match=message):
        period_of("nas", row)


def test_months_are_dated_by_their_first_day():
    assert period_of("cpi", {"year": "2026", "month": "August"}) == "2026-08-01"
    assert period_of("iip", {"year": 2026, "month": "January"}) == "2026-01-01"
    with pytest.raises(ValueError, match="not a month"):
        period_of("cpi", {"year": "2026", "month": "Aug"})


def test_the_back_series_is_reconstructed_and_spans_its_pages(env):
    c, _, mospi, _ = env
    first = [cpi(2024, "December", "102.90", "5.22", "Back"), cpi(2024, "November", "103.50", "5.48", "Back")]
    second = [cpi(2013, "January", "60.10", None, "Back")]
    report = mospi("cpi", request(c, "cpi", series="Back"), page(first, 1, 3, 2), page(second, 2, 3, 2))
    assert (report["pages"], report["rows"], report["values_recorded"], report["values_not_given"]) == (2, 3, 5, 1)
    rows = india_observations(c, "IN_CPI24B_GEN_INDEX", AFTER)
    assert [r["period"] for r in rows] == ["2013-01-01", "2024-11-01", "2024-12-01"]
    assert {r["status"] for r in rows} == {"reconstructed"}


def test_a_revision_is_a_new_vintage_and_the_old_value_stays_known_as_of_earlier(env):
    c, _, mospi, _ = env
    req = request(c, "cpi", series="Current")
    mospi("cpi", req, page(CPI_ROWS))
    later = READ + timedelta(days=30)
    report = mospi("cpi", req, page([cpi(2026, "August", "108.80", "4.85"), CPI_ROWS[1]]), read=later)
    assert (report["values_recorded"], report["already_present"]) == (2, 1)
    assert value(c, "IN_CPI24_GEN_INDEX", "2026-08-01") == 108.74
    assert value(c, "IN_CPI24_GEN_INDEX", "2026-08-01", later + timedelta(minutes=5)) == 108.80
    assert c.execute("SELECT COUNT(*) FROM mo_values WHERE series_id = 'IN_CPI24_GEN_INDEX'"
                     " AND period = '2026-08-01'").fetchone()[0] == 2


def test_the_same_pages_again_store_nothing(env):
    c, _, mospi, _ = env
    req = request(c, "cpi", series="Current")
    mospi("cpi", req, page(CPI_ROWS))
    with pytest.raises(ArtifactError, match="nothing new"):
        mospi("cpi", req, page(CPI_ROWS), read=READ + timedelta(days=1))
    assert c.execute("SELECT COUNT(*) FROM mo_reads").fetchone()[0] == 1


def test_an_unchanged_page_is_shared_with_the_read_that_stored_it(env):
    c, _, mospi, _ = env
    req = request(c, "cpi", series="Back")
    second = page([cpi(2013, "January", "60.10", None, "Back")], 2, 2, 2)
    mospi("cpi", req, page([cpi(2024, "December", "102.90", "5.22", "Back")], 1, 2, 2), second)
    report = mospi("cpi", req, page([cpi(2024, "December", "103.00", "5.30", "Back")], 1, 2, 2), second,
                   read=READ + timedelta(days=1))
    assert report["values_recorded"] == 2
    pages = c.execute("SELECT read_id, page, artifact_id FROM mo_pages ORDER BY read_id, page").fetchall()
    assert pages[1][2] == pages[3][2] and pages[0][2] != pages[2][2]


def test_a_period_with_two_values_in_one_answer_is_not_stored(env):
    c, _, mospi, _ = env
    report = mospi("cpi", request(c, "cpi", series="Current"),
                   page([cpi(2026, "August", "108.74", "4.82"), cpi(2026, "August", "109.00", "4.82")]))
    assert report["values_recorded"] == 1   # the inflation rate agrees
    assert any(p.startswith("period_conflict: IN_CPI24_GEN_INDEX 2026-08-01") for p in report["problems"])


def test_a_value_that_is_not_a_number_is_refused_and_recorded(env):
    c, _, mospi, _ = env
    report = mospi("cpi", request(c, "cpi", series="Current"), page([cpi(2026, "August", "NA", "4.82")]))
    assert report["values_recorded"] == 1 and report["rows_refused"] == 1
    assert c.execute("SELECT kind FROM mo_problems").fetchall() == [("row_refused",)]


@pytest.mark.parametrize("bodies, error, message", [
    ((b"<html>busy</html>",), MospiResponseError, "Not MoSPI's JSON"),
    ((b'{"error":"Please check the input parameters passed"}',), MospiResponseError, "input parameters"),
    ((page(CPI_ROWS, status=False),), MospiResponseError, "reported a failure"),
    ((b'{"data": [], "statusCode": true}',), MospiResponseError, "paged data list"),
    ((page([], total=0),), NoDataError, "no rows"),
    ((page(CPI_ROWS, number=2),), MospiResponseError, "page 2, not page 1"),
    ((page([], total=5),), MospiResponseError, "holds no rows"),
    ((page(CPI_ROWS, total=5, pages=2),), MospiResponseError, "cut short"),
    ((page(CPI_ROWS, total=4, pages=2), page(CPI_ROWS, 2, 5, 2)), MospiResponseError, "disagree on the totals"),
    ((page([cpi(2026, "August", "108.74", "4.82", sector="Rural")]),), MospiResponseError, "filter was not applied"),
])
def test_an_answer_that_cannot_be_used_is_refused_whole(env, bodies, error, message):
    c, _, mospi, _ = env
    with pytest.raises(error, match=message):
        mospi("cpi", request(c, "cpi", series="Current"), *bodies)
    assert c.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM mo_reads").fetchone()[0] == 0


def test_a_page_identical_to_another_sources_file_is_refused(env):
    from provenance.raw_store import store_raw_artifact
    c, _, mospi, tmp_path = env
    body = page(CPI_ROWS)
    (tmp_path / "other.json").write_bytes(body)
    store_raw_artifact(c, "fred_alfred", tmp_path / "other.json", READ, raw_dir=tmp_path / "raw")
    with pytest.raises(MospiResponseError, match="another source"):
        mospi("cpi", request(c, "cpi", series="Current"), body)


def test_a_read_is_known_only_once_its_last_page_was_read(env):
    c, _, mospi, _ = env
    first = [cpi(2024, "December", "102.90", "5.22", "Back")]
    mospi("cpi", request(c, "cpi", series="Back"), page(first, 1, 2, 2),
          page([cpi(2013, "January", "60.10", None, "Back")], 2, 2, 2))      # pages read at READ+1s and READ+2s
    assert india_observations(c, "IN_CPI24B_GEN_INDEX", READ + timedelta(seconds=1.5)) == []
    assert len(india_observations(c, "IN_CPI24B_GEN_INDEX", READ + timedelta(seconds=2))) == 2


def test_a_request_no_series_asks_for_is_refused(env):
    c, _, mospi, _ = env
    with pytest.raises(IndiaSeriesError, match="No registered series"):
        mospi("cpi", {"base_year": "2012"}, page(CPI_ROWS))


def test_read_page_checks_the_page_number():
    rows, meta = read_page(page(CPI_ROWS), 1)
    assert len(rows) == 2 and meta["totalPages"] == 1


# ---- availability (5A.1, 5B) --------------------------------------------------------------------

def test_mospi_values_support_current_decisions_from_this_systems_read_only(env):
    c, _, mospi, _ = env
    mospi("cpi", request(c, "cpi", series="Current"), page(CPI_ROWS))
    assert india_observations(c, "IN_CPI24_GEN_INDEX", READ - timedelta(minutes=1)) == []
    assert india_latest(c, "IN_CPI24_GEN_INDEX", AFTER)["period"] == "2026-08-01"
    assert india_observations(c, "IN_CPI24_GEN_INDEX", AFTER, REPLAY) == []   # no publication time: AVAILABILITY_REVIEW
    assert india_latest(c, "IN_CPI24_GEN_INDEX", AFTER, REPLAY) is None


# ---- the fetcher (ADR-009) ------------------------------------------------------------------------

class FakeMospi:
    def __init__(self, *answers):
        self.answers, self.urls = list(answers), []

    def get(self, url):
        self.urls.append(url)
        return self.answers.pop(0)


class Clock:
    def __init__(self):
        self.t, self.slept = 1000.0, []

    def __call__(self):
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += seconds


def client(fake):
    clock = Clock()
    return news_fetch.MospiClient(get=fake.get, sleep=clock.sleep, clock=clock, now=lambda: READ), clock


def test_the_fetcher_reads_every_page_then_stores_them(env):
    c, _, _, tmp_path = env
    req = request(c, "cpi", series="Back")
    fake = FakeMospi((200, page([cpi(2024, "December", "102.90", "5.22", "Back")], 1, 2, 2)),
                     (200, page([cpi(2013, "January", "60.10", None, "Back")], 2, 2, 2)))
    mospi_client, clock = client(fake)
    report = news_fetch.fetch_india_request(c, mospi_client, "cpi", req, tmp_path / "fetched", raw_dir=tmp_path / "raw")
    assert report["pages"] == 2 and report["values_recorded"] == 3 and clock.slept == [news_fetch.MOSPI_INTERVAL]
    first = news_fetch.urllib.parse.urlsplit(fake.urls[0])
    assert (first.scheme, first.netloc, first.path) == ("https", "api.mospi.gov.in", "/api/cpi/getCPIData")
    assert news_fetch.urllib.parse.parse_qs(first.query) == {k: [v] for k, v in {**req, "limit": "100", "page": "1"}.items()}
    assert "page=2" in fake.urls[1]
    assert len(list((tmp_path / "fetched").iterdir())) == 2


@pytest.mark.parametrize("answers, error, message", [
    (((500, b"error"),), news_fetch.FetchError, "HTTP 500"),
    (((429, b"slow down"),), news_fetch.RateLimited, "HTTP 429"),
    (((200, b"<html>"),), MospiResponseError, "Not MoSPI's JSON"),
    (((200, page(CPI_ROWS, total=2500, pages=25)),), MospiResponseError, "more than the 20 allowed"),
    (((200, page(CPI_ROWS[:1], 1, 2, 2)), (503, b"busy")), news_fetch.FetchError, "HTTP 503"),
])
def test_a_failed_fetch_stores_nothing(env, answers, error, message):
    c, _, _, tmp_path = env
    mospi_client, _ = client(FakeMospi(*answers))
    with pytest.raises(error, match=message):
        news_fetch.fetch_india_request(c, mospi_client, "cpi", request(c, "cpi", series="Current"), tmp_path / "f",
                                       raw_dir=tmp_path / "raw")
    assert c.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0] == 0 and not (tmp_path / "f").exists()


def test_mospi_is_not_asked_again_in_a_run_after_it_said_slow_down(env):
    c, _, _, tmp_path = env
    fake = FakeMospi((429, b"slow down"))
    mospi_client, _ = client(fake)
    for _ in range(2):
        with pytest.raises(news_fetch.RateLimited):
            news_fetch.fetch_india_request(c, mospi_client, "cpi", request(c, "cpi", series="Current"), tmp_path,
                                           raw_dir=tmp_path / "raw")
    assert len(fake.urls) == 1


def test_the_fetcher_asks_mospi_for_nothing_but_the_three_data_addresses():
    for url in ("https://api.mospi.gov.in/api/wpi/getWpiRecords?base_year=2022-23",
                "https://api.mospi.gov.in/api/rbi/getRbiRecords", "https://api.mospi.gov.in/api/users/usersignup",
                "https://api.mospi.gov.in:8443/api/cpi/getCPIData"):
        with pytest.raises(news_fetch.FetchError, match="not an allowed address"):
            news_fetch.http_get(url)
    for url in ("http://api.mospi.gov.in/api/cpi/getCPIData", "https://esankhyiki.mospi.gov.in/macroindicators"):
        with pytest.raises(news_fetch.FetchError, match="not an allowed host"):
            news_fetch.http_get(url)


def test_only_mospi_gets_the_old_tls_option_and_certificates_are_always_checked():
    import ssl
    for host in ("api.mospi.gov.in", "api.stlouisfed.org", "api.gdeltproject.org", "www.sebi.gov.in"):
        context = news_fetch.tls_context(host)
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        assert bool(context.options & getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)) == (host == "api.mospi.gov.in")


def test_no_code_switches_certificate_checking_off():
    pattern = re.compile(r"CERT_NONE|check_hostname\s*=\s*False|_create_unverified_context|verify\s*=\s*False")
    files = list((PROJECT_ROOT / "src").rglob("*.py")) + [PROJECT_ROOT / "manage.py"]
    assert [p.name for p in files if pattern.search(p.read_text(encoding="utf-8"))] == []


def test_no_code_reads_wpi_or_rbi_tables_from_mospi():
    files = list((PROJECT_ROOT / "src").rglob("*.py")) + [PROJECT_ROOT / "manage.py"]
    assert [p.name for p in files if re.search(r"/api/(wpi|rbi)/", p.read_text(encoding="utf-8"))] == []


# ---- registry, migration and acceptance record ---------------------------------------------------

def test_mospi_and_the_calendars_are_registered_with_their_terms(env):
    c, *_ = env
    mospi = get_source(c, "mospi_esankhyiki")
    assert mospi["source_class"] == "official_statistics" and mospi["authority"] == "primary"
    assert "Category A" in mospi["license"] and "attribution" in mospi["license"] and "not used" in mospi["license"]
    cal = get_source(c, "market_calendars")
    assert "Apache License 2.0" in cal["license"] and (PROJECT_ROOT / "docs" / "third_party"
                                                       / "exchange_calendars-LICENSE.txt").exists()
    assert ATTRIBUTION.startswith("Source: Ministry of Statistics and Programme Implementation")


def test_india_tables_are_append_only(env):
    c, _, mospi, _ = env
    mospi("cpi", request(c, "cpi", series="Current"), page(CPI_ROWS))
    c.execute("INSERT INTO mo_problems VALUES (1, 'x', 'x')")
    for sql in ("UPDATE mo_values SET value = 0", "DELETE FROM mo_values", "UPDATE mo_series SET title = 'x'",
                "DELETE FROM mo_series", "UPDATE mo_reads SET rows = 0", "DELETE FROM mo_reads",
                "UPDATE mo_pages SET page = 9", "DELETE FROM mo_pages", "UPDATE mo_problems SET kind = 'y'",
                "DELETE FROM mo_problems"):
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            c.execute(sql)


def test_the_india_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 17)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not [n for n in names if n.startswith("mo_")] and "mc_vintages" in names
    c.close()


def test_stage_10c2_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_10C2_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_INDIA_MACRO_AND_CALENDARS_BASELINE"
    assert record["negative_assertions"]["value on a day its market was closed used as a close"] is False
    assert record["negative_assertions"]["certificate checking switched off"] is False
