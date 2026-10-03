"""Stage 10C tests: global and India macro context from FRED/ALFRED (architecture 40B step 9a, 3G, 4C,
4G, 5, 5A, 5B, 5C; ADR-008).

Built on FRED's real answers of 03-Oct-2026: US Treasury 10-year yields published the next business
day (the value for 1 October first shown on 2 October), a holiday listed without a value (US Labor
Day, '.'), US payrolls revised twice, daily series too long for FRED's 2,000-vintage-date limit, and
series descriptions with FRED's last update and its UTC offset ('2026-10-02 15:16:37-05'). Figures of
US government series are real; values of index series owned by others (Nasdaq, Nikkei) are made up,
so nothing owned by them is published here.
"""
import json
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone

import pytest

from core.config import PROJECT_ROOT
from core.database import connect, migrate, rollback
from core.sessions import SessionError, local_to_utc
from data_quality.missing_data import MissingClass
from data_quality.trust_chain import NoDataError
from ingestion import news_fetch
from ingestion.macro_context import (ALL_VINTAGES, EXCLUDED_SERIES, FRED_NOTICE, FREQUENCIES, GROUPS,
                                     LOOKBACK, OPEN_END, VINTAGE_WINDOW, MacroResponseError, MacroSeriesError,
                                     check_entry, latest, load_fred_answers, load_series_file, observations,
                                     request_for, series_info, sync_series, value_on)
from ingestion.source_registry import SourceRegistryError, get_source, sync_sources
from provenance.availability import PitClaim
from provenance.raw_store import ArtifactError

UTC = timezone.utc
REPLAY = PitClaim.HISTORICAL_REPLAY
KEY = "0123456789abcdef0123456789abcdef"     # a made-up key of FRED's shape
READ = datetime(2026, 10, 3, 14, 39, tzinfo=UTC)
WINDOW = (READ.date() - VINTAGE_WINDOW).isoformat()
H15_UPDATE = "2026-10-02 15:16:37-05"        # FRED's real last update of DGS10, i.e. 20:16:37 UTC
# DGS10, real: each value first shown the next business day; Labor Day (7 September) has no value.
DGS10 = [("2026-09-03", "4.77", "2026-09-04"), ("2026-09-04", "4.78", "2026-09-08"), ("2026-09-07", ".", "2026-09-08"),
         ("2026-09-08", "4.8", "2026-09-09"), ("2026-09-14", "4.97", "2026-09-15"), ("2026-09-30", "5.29", "2026-10-01"),
         ("2026-10-01", "5.24", "2026-10-02")]


def rows(spec):
    """FRED observation rows from (date, value, realtime_start[, realtime_end])."""
    return [{"realtime_start": s[2], "realtime_end": s[3] if len(s) > 3 else OPEN_END, "date": s[0], "value": s[1]}
            for s in spec]


def answer(found, asked, **header):
    doc = {"realtime_start": asked["realtime_start"], "realtime_end": asked["realtime_end"],
           "observation_start": asked["observation_start"], "observation_end": "9999-12-31", "units": "lin",
           "output_type": 1, "file_type": "json", "order_by": "observation_date", "sort_order": "asc",
           "count": len(found), "offset": 0, "limit": 100000, "observations": found}
    doc.update(header)
    return json.dumps(doc).encode()


@pytest.fixture
def env(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    sync_series(c)
    files = iter(range(1000))

    def ask(sid, start=None, realtime_start=None):
        info = series_info(c, sid)
        window = WINDOW if info["frequency"] in ("daily", "daily_7day") else ALL_VINTAGES
        return {"series_id": sid, "observation_start": start or info["history_from"],
                "realtime_start": realtime_start or window, "realtime_end": OPEN_END}

    def describe(sid, updated=H15_UPDATE, **changes):
        info = series_info(c, sid)
        meta = {"id": sid, "title": info["title"], "frequency_short": FREQUENCIES[info["frequency"]],
                "units": info["fred_units"], "last_updated": updated, "notes": "For questions on the data ..."}
        meta.update(changes)
        return json.dumps({"realtime_start": "2026-10-02", "realtime_end": "2026-10-02", "seriess": [meta]}).encode()

    def load(sid, spec=(), asked=None, read=READ, updated=H15_UPDATE, obs=None, meta=None, meta_read=None):
        asked = asked or ask(sid)
        n = next(files)
        obs_path, meta_path = tmp_path / f"obs_{n}.json", tmp_path / f"meta_{n}.json"
        obs_path.write_bytes(obs if obs is not None else answer(rows(spec), asked))
        meta_path.write_bytes(meta if meta is not None else describe(sid, updated))
        return load_fred_answers(c, sid, obs_path, read, meta_path, meta_read or read + timedelta(seconds=2), asked,
                                 raw_dir=tmp_path / "raw")

    yield c, load, ask, describe, tmp_path
    c.close()


def count(c, table):
    return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def at(text):
    return datetime.fromisoformat(text)


def india(day, hhmm):
    return datetime.fromisoformat(f"{day}T{hhmm}:00+05:30")


# ---- market time (core/sessions.py, 5C rule 1) -------------------------------------------------

@pytest.mark.parametrize("day, hhmm, zone, utc", [
    ("2026-07-01", "16:00", "America/New_York", "2026-07-01T20:00:00+00:00"),   # daylight saving
    ("2026-12-01", "16:00", "America/New_York", "2026-12-01T21:00:00+00:00"),   # standard time
    ("2026-03-06", "16:00", "America/New_York", "2026-03-06T21:00:00+00:00"),   # Friday before the change
    ("2026-03-09", "16:00", "America/New_York", "2026-03-09T20:00:00+00:00"),   # Monday after (8 March)
    ("2026-10-30", "16:00", "America/New_York", "2026-10-30T20:00:00+00:00"),   # Friday before 1 November
    ("2026-11-02", "16:00", "America/New_York", "2026-11-02T21:00:00+00:00"),
    ("2026-03-08", "00:30", "America/New_York", "2026-03-08T05:30:00+00:00"),   # changeover day, before 01:00
    ("2026-03-08", "03:00", "America/New_York", "2026-03-08T07:00:00+00:00"),   # changeover day, after
    ("2026-11-01", "00:30", "America/New_York", "2026-11-01T04:30:00+00:00"),
    ("2026-11-01", "03:00", "America/New_York", "2026-11-01T08:00:00+00:00"),
    ("2026-01-05", "01:30", "America/New_York", "2026-01-05T06:30:00+00:00"),   # an ordinary day at 01:30
    ("2026-10-02", "15:30", "Asia/Tokyo", "2026-10-02T06:30:00+00:00"),
    ("2026-10-02", "15:30", "Asia/Kolkata", "2026-10-02T10:00:00+00:00"),
])
def test_session_times_are_placed_in_utc_by_their_own_zone(day, hhmm, zone, utc):
    assert local_to_utc(day, hhmm, zone).isoformat() == utc


@pytest.mark.parametrize("day, hhmm, zone, message", [
    ("2026-10-02", "16:00", "Europe/London", "not declared"),
    ("2006-12-01", "16:00", "America/New_York", "before 2007-03-11"),
    ("2026-03-08", "02:30", "America/New_York", "changeover"),
    ("2026-11-01", "01:30", "America/New_York", "changeover"),
    ("2026-10-02", "24:00", "America/New_York", "HH:MM"),
    ("2026-10-02", "9:30", "America/New_York", "HH:MM"),
    ("20261002", "16:00", "America/New_York", "YYYY-MM-DD"),
])
def test_a_time_that_cannot_be_placed_safely_is_refused(day, hhmm, zone, message):
    with pytest.raises((SessionError, ValueError), match=message):
        local_to_utc(day, hhmm, zone)


# ---- the series registry (3G, 5C rule 1) ----------------------------------------------------------

def test_every_declared_series_is_valid_and_recorded(env):
    c, *_ = env
    declared = load_series_file()
    assert len(declared) == 25 and count(c, "mc_series") == 25
    groups = {e["group"] for e in declared}
    assert groups == set(GROUPS)
    assert not {e["series_id"] for e in declared} & EXCLUDED_SERIES
    for entry in declared:
        info = series_info(c, entry["series_id"])
        assert info["time_zone"] and info["calendar"] and info["market"] and info["licence"]
        assert (info["kind"] == "market_close") == (info["session_close"] is not None)
    assert sync_series(c) == []   # a second sync records nothing new


def test_the_market_closes_are_declared_where_they_are_set():
    closes = {e["series_id"]: (e["time_zone"], e["session_close"]) for e in load_series_file() if "session_close" in e}
    assert closes == {"NASDAQCOM": ("America/New_York", "16:00"), "NIKKEI225": ("Asia/Tokyo", "15:30"),
                      "VIXCLS": ("America/New_York", "16:15"), "VXEEMCLS": ("America/New_York", "16:15"),
                      "BAMLH0A0HYM2": ("America/New_York", "17:00"), "BAMLEMCBPIOAS": ("America/New_York", "17:00")}


GOOD = {"series_id": "DGS5", "title": "US Treasury 5-year yield", "group": "rates_and_bonds", "region": "United States",
        "kind": "published_statistic", "market": "Federal Reserve Board, H.15", "calendar": "US business days",
        "time_zone": "America/New_York", "frequency": "daily", "fred_units": "Percent",
        "history_from": "2016-01-01", "licence": "US government data"}
CLOSE = {**GOOD, "series_id": "NIKKEI300", "kind": "market_close", "time_zone": "Asia/Tokyo", "session_close": "15:30"}


@pytest.mark.parametrize("entry, message", [
    ({**GOOD, "series_id": "SP500"}, "forbids reproduction"),
    ({**GOOD, "series_id": "DJIA"}, "forbids reproduction"),
    ({**GOOD, "series_id": "dgs5"}, "not a FRED series id"),
    ({**GOOD, "kind": "guess"}, "kind"),
    ({**GOOD, "group": "flows"}, "group"),
    ({**GOOD, "frequency": "hourly"}, "frequency"),
    ({**GOOD, "history_from": "2016-1-1"}, "history_from"),
    ({**GOOD, "title": ""}, "empty fields"),
    ({**GOOD, "colour": "red"}, "unknown fields"),
    ({k: v for k, v in GOOD.items() if k != "licence"}, "missing fields"),
    ({**GOOD, "session_close": "16:00"}, "only a market close"),
    ({**GOOD, "time_zone": "Eastern"}, "Area/City"),
    ({k: v for k, v in CLOSE.items() if k != "session_close"}, "session_close"),
    ({**CLOSE, "time_zone": "Europe/London"}, "a market close needs a time zone declared"),
    ({**CLOSE, "frequency": "monthly"}, "daily"),
    ({**CLOSE, "session_close": "25:00"}, "cannot be placed in time"),
    ("DGS5", "set of fields"),
])
def test_a_series_declared_wrongly_is_refused(entry, message):
    with pytest.raises(MacroSeriesError, match=message):
        check_entry(entry)


def test_a_good_declaration_is_accepted():
    assert check_entry(GOOD)["session_close"] is None
    assert check_entry(CLOSE)["session_close"] == "15:30"


def test_recorded_series_are_never_silently_changed(env, tmp_path):
    c, *_ = env
    text = (PROJECT_ROOT / "config" / "macro_series.yaml").read_text(encoding="utf-8")
    changed = tmp_path / "changed.yaml"
    changed.write_text(text.replace("fred_units: Indian Rupees to One U.S. Dollar", "fred_units: Rupees"),
                       encoding="utf-8")
    with pytest.raises(MacroSeriesError, match="never silently changed"):
        sync_series(c, changed)
    removed = tmp_path / "removed.yaml"
    removed.write_text(text.replace("  - series_id: GDPC1", "  - series_id: GDPC1X"), encoding="utf-8")
    with pytest.raises(MacroSeriesError, match="no longer declared"):
        sync_series(c, removed)
    twice = tmp_path / "twice.yaml"
    twice.write_text(text.replace("series_id: GDPC1", "series_id: PAYEMS"), encoding="utf-8")
    with pytest.raises(MacroSeriesError, match="declared twice"):
        sync_series(c, twice)
    assert count(c, "mc_series") == 25


def test_series_need_the_fred_source_registered_first():
    c = connect(":memory:")
    migrate(c)
    with pytest.raises(SourceRegistryError):
        sync_series(c)
    c.close()


# ---- what is asked for ------------------------------------------------------------------------

def test_the_first_fetch_asks_the_whole_history_later_ones_a_look_back(env):
    c, load, ask, *_ = env
    assert request_for(c, "DGS10", READ.date()) == (ask("DGS10"), {"series_id": "DGS10"})
    assert ask("DGS10")["realtime_start"] == "2023-10-04"            # a rolling 3-year real-time window
    assert request_for(c, "PAYEMS", READ.date())[0]["realtime_start"] == ALL_VINTAGES   # every vintage
    load("DGS10", DGS10)
    asked, _ = request_for(c, "DGS10", READ.date())
    assert asked["observation_start"] == (date(2026, 10, 1) - LOOKBACK["daily"]).isoformat()
    assert request_for(c, "DGS10", READ.date(), full=True)[0]["observation_start"] == "2016-01-01"
    with pytest.raises(MacroSeriesError, match="not a registered series"):
        request_for(c, "SP500", READ.date())


# ---- answers refused whole (4C.1, 4G rules 6-7) ------------------------------------------------------

@pytest.mark.parametrize("body, error, message", [
    (b"<html>maintenance</html>", MacroResponseError, "Not FRED's JSON"),
    (b'{"error_code":400,"error_message":"Bad Request.  The series does not exist."}', MacroResponseError,
     "series does not exist"),
    (b"[1, 2]", MacroResponseError, "not an object"),
    (json.dumps({"observations": []}).encode(), MacroResponseError, "no \\['realtime_start'"),
])
def test_an_answer_that_is_not_an_observation_list_is_refused_whole(env, body, error, message):
    c, load, *_ = env
    with pytest.raises(error, match=message):
        load("DGS10", obs=body)
    assert count(c, "raw_artifacts") == count(c, "mc_responses") == count(c, "mc_vintages") == 0


@pytest.mark.parametrize("change, error, message", [
    ({"realtime_start": "2026-09-15"}, MacroResponseError, "not the '2023-10-04' asked for"),
    ({"observation_start": "2026-09-01"}, MacroResponseError, "observation_start"),
    ({"units": "chg"}, MacroResponseError, "plain levels"),
    ({"output_type": 4}, MacroResponseError, "plain levels"),
    ({"count": 9}, MacroResponseError, "cut short"),
    ({"observations": {}}, MacroResponseError, "not a list"),
    ({"observations": [], "count": 0}, NoDataError, "no observations"),
])
def test_an_answer_not_matching_the_request_is_refused_whole(env, change, error, message):
    c, load, ask, *_ = env
    with pytest.raises(error, match=message):
        load("DGS10", obs=answer(rows(DGS10), ask("DGS10"), **change))
    assert count(c, "raw_artifacts") == count(c, "mc_vintages") == 0


@pytest.mark.parametrize("change, message", [
    ({"id": "DGS2"}, "not DGS10"),
    ({"units": "Basis Points"}, "registry says 'Percent'"),
    ({"frequency_short": "M"}, "frequency"),
    ({"last_updated": "2026-10-02T15:16:37Z"}, "Not FRED's time format"),
    ({"last_updated": "2026-10-03 15:00:00-05"}, "later than our read"),
    ({"notes": "Copyright S&P Dow Jones Indices LLC. All rights reserved."}, "forbid reproduction"),
])
def test_a_series_description_that_disagrees_with_the_registry_is_refused(env, change, message):
    c, load, _, describe, _ = env
    with pytest.raises(MacroResponseError, match=message):
        load("DGS10", DGS10, meta=describe("DGS10", **change))
    assert count(c, "raw_artifacts") == count(c, "mc_vintages") == 0


def test_the_description_must_be_read_after_the_observations(env):
    c, load, *_ = env
    with pytest.raises(MacroResponseError, match="after the observations"):
        load("DGS10", DGS10, meta_read=READ - timedelta(seconds=1))
    assert count(c, "raw_artifacts") == 0


# ---- vintages (3G rule 1, 5, 5A) ------------------------------------------------------------------------

def test_an_answer_is_kept_and_its_vintages_stored(env):
    c, load, *_ = env
    report = load("DGS10", DGS10)
    assert (report["rows"], report["vintages_recorded"], report["already_present"], report["rows_refused"]) == (7, 7, 0, 0)
    assert report["newest_date"] == "2026-10-01" and report["fred_updated"] == "2026-10-02T15:16:37-05:00"
    assert {r[0] for r in c.execute("SELECT source_id FROM raw_artifacts")} == {"fred_alfred"}
    request = json.loads(c.execute("SELECT request FROM mc_responses").fetchone()[0])
    assert request["series_id"] == "DGS10" and "api_key" not in request
    stored = c.execute("SELECT obs_date, value, missing_class, value_text, realtime_start, start_clipped, set_at,"
                       " available_at FROM mc_vintages WHERE obs_date IN ('2026-09-07', '2026-10-01')"
                       " ORDER BY obs_date").fetchall()
    assert stored == [("2026-09-07", None, "structurally_absent", ".", "2026-09-08", 0, None, "2026-10-02T20:16:37+00:00"),
                      ("2026-10-01", 5.24, None, "5.24", "2026-10-02", 0, None, "2026-10-02T20:16:37+00:00")]


def test_values_read_again_are_not_stored_twice(env):
    c, load, *_ = env
    load("DGS10", DGS10[:5], read=at("2026-09-15T21:00:00+00:00"), updated="2026-09-15 15:16:37-05")
    report = load("DGS10", DGS10)
    assert (report["vintages_recorded"], report["already_present"]) == (2, 5)
    assert count(c, "mc_vintages") == 7 and count(c, "mc_responses") == 2
    with pytest.raises(ArtifactError, match="already ingested"):   # the very same bytes again
        load("DGS10", DGS10, read=READ + timedelta(hours=1))
    assert count(c, "mc_responses") == 2


PAYEMS_JULY = [("2026-06-01", "158984", "2026-07-02")]   # real: June first published 2 July
PAYEMS_AUGUST = [("2026-06-01", "158984", "2026-07-02", "2026-08-06"), ("2026-06-01", "158881", "2026-08-07"),
                 ("2026-07-01", "158858", "2026-08-07")]


def test_a_revision_is_a_new_vintage_and_the_original_stays_known_as_of_earlier(env):
    # 40B step 4 for macro data: read a value, read its revision later, ask as of before the revision.
    c, load, *_ = env
    july, august = datetime(2026, 7, 10, 6, tzinfo=UTC), datetime(2026, 8, 10, 6, tzinfo=UTC)
    load("PAYEMS", PAYEMS_JULY, read=july, updated="2026-07-02 08:24:33-05")
    report = load("PAYEMS", PAYEMS_AUGUST, read=august, updated="2026-08-07 08:24:33-05")
    assert (report["vintages_recorded"], report["already_present"]) == (2, 1)
    # Current decisions learn of the revision when this system read it (10 August) ...
    assert value_on(c, "PAYEMS", "2026-06-01", august - timedelta(days=1))["value"] == 158984
    assert value_on(c, "PAYEMS", "2026-06-01", august + timedelta(hours=1))["value"] == 158881
    # ... replay from FRED's own update of 7 August, 13:24 UTC - read with the revision, so proven.
    assert value_on(c, "PAYEMS", "2026-06-01", at("2026-08-07T13:00:00+00:00"), REPLAY)["value"] == 158984
    assert value_on(c, "PAYEMS", "2026-06-01", at("2026-08-07T13:30:00+00:00"), REPLAY)["value"] == 158881
    assert value_on(c, "PAYEMS", "2026-06-01", july - timedelta(days=1))["missing_class"] == \
        MissingClass.NOT_YET_RELEASED
    june = [r for r in observations(c, "PAYEMS", august + timedelta(hours=1)) if r["date"] == "2026-06-01"]
    assert june[0]["realtime_start"] == "2026-08-07"


def test_a_vintage_read_again_with_another_value_is_a_conflict(env):
    c, load, *_ = env
    load("PAYEMS", PAYEMS_JULY, read=datetime(2026, 7, 10, 6, tzinfo=UTC), updated="2026-07-02 08:24:33-05")
    report = load("PAYEMS", [("2026-06-01", "999999", "2026-07-02")], read=datetime(2026, 7, 11, 6, tzinfo=UTC),
                  updated="2026-07-02 08:24:33-05")
    assert report["vintages_recorded"] == 0 and report["rows_refused"] == 1
    assert report["problems"][0].startswith("vintage_conflict: row 1: 2026-06-01 from 2026-07-02")
    assert c.execute("SELECT value FROM mc_vintages").fetchall() == [(158984.0,)]


def test_a_later_vintage_contradicting_a_stored_one_within_its_period_is_a_conflict(env):
    c, load, *_ = env
    load("PAYEMS", PAYEMS_AUGUST, read=datetime(2026, 8, 10, 6, tzinfo=UTC), updated="2026-08-07 08:24:33-05")
    report = load("PAYEMS", [("2026-06-01", "158900", "2026-08-01")], read=datetime(2026, 8, 11, 6, tzinfo=UTC),
                  updated="2026-08-07 08:24:33-05")
    assert report["problems"][0].startswith("vintage_conflict")


def test_a_clipped_start_is_marked_and_never_taken_for_a_new_vintage(env):
    # FRED reports a value older than the window asked for as starting on the window's first day.
    c, load, ask, *_ = env
    old = [("2016-01-04", "2.24", WINDOW), ("2026-10-01", "5.24", "2026-10-02")]
    load("DGS10", old)
    assert c.execute("SELECT start_clipped FROM mc_vintages ORDER BY obs_date").fetchall() == [(1,), (0,)]
    later = (date.fromisoformat(WINDOW) + timedelta(days=1)).isoformat()
    report = load("DGS10", [("2016-01-04", "2.24", later)], asked=ask("DGS10", realtime_start=later),
                  read=READ + timedelta(days=1))
    assert (report["vintages_recorded"], report["already_present"]) == (0, 1)
    report = load("DGS10", [("2016-01-04", "2.30", later)], asked=ask("DGS10", realtime_start=later),
                  read=READ + timedelta(days=2))
    assert report["vintages_recorded"] == 1   # a revision this system had not seen; its start is unknown
    found = value_on(c, "DGS10", "2016-01-04", READ + timedelta(days=3))
    assert (found["value"], found["start_clipped"]) == (2.30, True)
    assert value_on(c, "DGS10", "2016-01-04", READ + timedelta(hours=1))["value"] == 2.24


@pytest.mark.parametrize("bad, message", [
    ({"date": "2026-9-30", "value": "5.29", "realtime_start": "2026-10-01", "realtime_end": OPEN_END}, "YYYY-MM-DD"),
    ({"date": "2026-09-30", "value": "ND", "realtime_start": "2026-10-01", "realtime_end": OPEN_END}, "not a number"),
    ({"date": "2026-09-30", "value": "5.29", "realtime_start": "2026-10-01", "realtime_end": "2026-09-30"},
     "end 2026-09-30 is before its start"),
    ({"date": "2026-09-30", "value": "5.29", "realtime_start": "2026-10-09", "realtime_end": OPEN_END},
     "after this answer was read"),
    ({"date": "2016-01-04", "value": "2.24", "realtime_start": "2020-01-02", "realtime_end": OPEN_END},
     "before the window asked for"),
    ({"date": "2026-09-30", "value": "5.29"}, "a row without"),
])
def test_unusable_rows_are_refused_and_recorded(env, bad, message):
    c, load, ask, *_ = env
    report = load("DGS10", obs=answer(rows(DGS10[-1:]) + [bad], ask("DGS10")))
    assert (report["vintages_recorded"], report["rows_refused"]) == (1, 1)
    assert re.search(message, report["problems"][0]) and report["problems"][0].startswith("row_refused: row 2")
    assert c.execute("SELECT kind FROM mc_problems").fetchall() == [("row_refused",)]


def test_monthly_values_must_be_dated_by_the_first_day_of_the_month(env):
    c, load, *_ = env
    report = load("PAYEMS", [("2026-06-01", "158984", "2026-07-02"), ("2026-06-15", "158984", "2026-07-02")],
                  read=datetime(2026, 7, 10, tzinfo=UTC), updated="2026-07-02 08:24:33-05")
    assert report["rows_refused"] == 1 and "not the first day of a month" in report["problems"][0]
    with pytest.raises(ValueError, match="first day of each month"):
        value_on(c, "PAYEMS", "2026-06-15", READ)
    with pytest.raises(ValueError, match="first day of each quarter"):
        value_on(c, "GDPC1", "2026-05-01", READ)


# ---- availability: current decision and historical replay (5B) -----------------------------------------

def test_current_decisions_use_this_systems_read_and_replay_uses_freds_own_update_time(env):
    c, load, *_ = env
    load("DGS10", DGS10)   # read 03-Oct 14:39 UTC; FRED's last update 02-Oct 20:16:37 UTC
    before_read, after_read = READ - timedelta(minutes=30), READ + timedelta(minutes=1)
    assert value_on(c, "DGS10", "2026-10-01", before_read)["missing_class"] == MissingClass.NOT_YET_RELEASED
    assert value_on(c, "DGS10", "2026-10-01", after_read)["value"] == 5.24
    assert value_on(c, "DGS10", "2026-10-01", before_read, REPLAY)["value"] == 5.24
    assert value_on(c, "DGS10", "2026-10-01", at("2026-10-02T20:00:00+00:00"), REPLAY)["missing_class"] == \
        MissingClass.NOT_YET_RELEASED
    assert observations(c, "DGS10", after_read)[-1]["available_at"] == READ.isoformat()
    assert observations(c, "DGS10", after_read, REPLAY)[-1]["available_at"] == "2026-10-02T20:16:37+00:00"


def test_a_value_is_proven_public_no_later_than_this_systems_own_read(env):
    # FRED updated the series between our two requests: the values were public at our first read anyway.
    c, load, *_ = env
    load("DGS10", DGS10, updated="2026-10-03 09:39:01-05", meta_read=READ + timedelta(seconds=2))
    assert c.execute("SELECT DISTINCT available_at FROM mc_vintages").fetchall() == [(READ.isoformat(),)]


def test_history_older_than_the_first_read_is_not_replayable_on_alfreds_dates_alone(env):
    # ALFRED says the value for 14 September was first shown on 15 September; that date is kept, but the
    # proof of availability is FRED's update time read by this system (ICE's real dates precede FRED's loads).
    c, load, *_ = env
    load("DGS10", DGS10)
    assert value_on(c, "DGS10", "2026-09-14", at("2026-09-20T00:00:00+00:00"), REPLAY)["missing_class"] == \
        MissingClass.NOT_YET_RELEASED
    assert observations(c, "DGS10", READ + timedelta(hours=1))[4]["realtime_start"] == "2026-09-15"


# ---- cross-market timing (5C, criteria 90-91) --------------------------------------------------------------

NASDAQ_UPDATE = "2026-10-01 22:38:54-05"   # 02-Oct 03:38:54 UTC, as FRED updated the real series


def test_a_us_close_is_not_available_to_the_indian_session_of_the_same_date(env):
    # Nasdaq closes at 16:00 New York time - 01:30 the next morning in India.
    c, load, *_ = env
    load("NASDAQCOM", [("2026-10-01", "1000.50", "2026-10-01")], read=at("2026-10-02T04:00:00+00:00"),
         updated=NASDAQ_UPDATE)
    [stored] = c.execute("SELECT set_at, available_at FROM mc_vintages").fetchall()
    assert stored == ("2026-10-01T20:00:00+00:00", "2026-10-02T03:38:54+00:00")
    for claim in (PitClaim.CURRENT_DECISION, REPLAY):
        same_day = value_on(c, "NASDAQCOM", "2026-10-01", india("2026-10-01", "14:00"), claim)
        assert same_day["value"] is None and same_day["missing_class"] == MissingClass.NOT_YET_RELEASED
    assert value_on(c, "NASDAQCOM", "2026-10-01", india("2026-10-02", "09:15"), REPLAY)["value"] == 1000.50
    assert value_on(c, "NASDAQCOM", "2026-10-01", india("2026-10-02", "09:15"))["missing_class"] == \
        MissingClass.NOT_YET_RELEASED          # this system read it at 09:30 India time
    assert value_on(c, "NASDAQCOM", "2026-10-01", india("2026-10-02", "09:45"))["value"] == 1000.50


def test_a_close_shown_before_its_session_ended_is_refused(env):
    c, load, *_ = env
    report = load("NASDAQCOM", [("2026-10-01", "1000.50", "2026-10-01")], read=at("2026-10-01T19:30:00+00:00"),
                  updated="2026-10-01 14:00:00-05")
    assert report["vintages_recorded"] == 0
    assert report["problems"][0].startswith("published_before_close: row 1: 2026-10-01: FRED shows this close by"
                                            " 2026-10-01 19:00 UTC, before that session ended (2026-10-01 20:00 UTC)")


def test_the_proof_decides_and_the_session_close_only_bounds_it(env):
    # Tokyo closes at 12:00 India time, but FRED had the Nikkei close only at 17:32 India time.
    c, load, *_ = env
    load("NIKKEI225", [("2026-10-02", "100.25", "2026-10-02")], read=at("2026-10-02T12:30:00+00:00"),
         updated="2026-10-02 07:02:36-05")
    assert c.execute("SELECT set_at FROM mc_vintages").fetchone()[0] == "2026-10-02T06:30:00+00:00"
    assert value_on(c, "NIKKEI225", "2026-10-02", india("2026-10-02", "12:30"), REPLAY)["value"] is None
    assert value_on(c, "NIKKEI225", "2026-10-02", india("2026-10-02", "18:00"), REPLAY)["value"] == 100.25


def test_a_close_is_never_used_before_its_session_ended_even_if_a_row_says_otherwise(env):
    # Defence in depth: a row stored by any route still waits for its session close.
    c, *_ = env
    c.execute("INSERT INTO raw_artifacts (source_id, sha256, original_name, stored_path, byte_size, retrieved_at,"
              " recorded_at) VALUES ('fred_alfred', 'x', 'x', 'x', 1, '2026-10-01T19:00:00+00:00', 'x')")
    c.execute("INSERT INTO mc_responses VALUES (1, 'NASDAQCOM', 1, 1, '{}', 'x', 'x', 1, 1, 0, 0, 'x')")
    c.execute("INSERT INTO mc_vintages (series_id, obs_date, value, value_text, realtime_start, start_clipped, set_at,"
              " available_at, response_id, recorded_at) VALUES ('NASDAQCOM', '2026-10-01', 1000.5, '1000.5',"
              " '2026-10-01', 0, '2026-10-01T20:00:00+00:00', '2026-10-01T20:30:00+00:00', 1, 'x')")
    assert value_on(c, "NASDAQCOM", "2026-10-01", at("2026-10-01T19:30:00+00:00"))["value"] is None
    assert value_on(c, "NASDAQCOM", "2026-10-01", at("2026-10-01T20:30:00+00:00"))["value"] == 1000.5


def test_every_value_carries_its_session_time_zone_publication_and_vintage(env):
    # 40B step 9a: "Every series carries session, time zone, publication time and vintages".
    c, load, *_ = env
    load("DGS10", DGS10)
    load("NASDAQCOM", [("2026-10-01", "1000.50", "2026-10-01")], read=at("2026-10-02T04:00:00+00:00"),
         updated=NASDAQ_UPDATE)
    for sid in ("DGS10", "NASDAQCOM"):
        info = series_info(c, sid)
        assert info["time_zone"] and info["calendar"]
        for r in observations(c, sid, READ + timedelta(hours=1)):
            assert r["realtime_start"] and r["available_at"] and r["value_text"]
            assert (r["set_at"] is not None) == (info["kind"] == "market_close")


# ---- absence is classified, never carried forward (4C, 5C rule 4) ---------------------------------------------

def test_a_holiday_is_structurally_absent_and_never_filled_from_the_day_before(env):
    c, load, *_ = env
    load("DGS10", DGS10)
    found = value_on(c, "DGS10", "2026-09-07", READ + timedelta(hours=1))
    assert found["value"] is None and found["missing_class"] == MissingClass.STRUCTURALLY_ABSENT
    assert "without a value" in found["reason"] and found["value_text"] == "."


@pytest.mark.parametrize("day, wanted, reason", [
    ("2026-09-05", MissingClass.STRUCTURALLY_ABSENT, "weekend"),        # a Saturday
    ("2026-10-02", MissingClass.NOT_YET_RELEASED, "not published"),     # published only on the next business day
    ("2015-12-31", MissingClass.EXTRACTION_FAILURE, "before the stored history"),
    ("2026-09-10", MissingClass.EXTRACTION_FAILURE, "no row for this date"),
])
def test_a_date_without_a_stored_value_says_why(env, day, wanted, reason):
    c, load, *_ = env
    load("DGS10", DGS10)
    found = value_on(c, "DGS10", day, READ + timedelta(hours=1))
    assert found["value"] is None and found["missing_class"] == wanted and reason in found["reason"]


def test_a_seven_day_series_has_no_weekend_exemption(env):
    c, load, *_ = env
    load("DFF", [("2026-09-04", "3.88", "2026-09-08"), ("2026-09-07", "3.88", "2026-09-08")])
    found = value_on(c, "DFF", "2026-09-05", READ)
    assert found["missing_class"] == MissingClass.EXTRACTION_FAILURE


def test_the_latest_value_keeps_its_own_date_and_age(env):
    c, load, *_ = env
    load("DGS10", DGS10[:3], read=at("2026-09-08T21:00:00+00:00"), updated="2026-09-08 15:16:37-05")
    found = latest(c, "DGS10", at("2026-09-09T04:00:00+00:00"))
    assert (found["date"], found["value"], found["age_days"]) == ("2026-09-04", 4.78, 5)
    assert found["later_dates_without_value"] == ["2026-09-07"]
    assert latest(c, "DGS10", at("2026-09-01T00:00:00+00:00")) is None


# ---- the fetcher (ADR-008, 4G rules 4-5) -------------------------------------------------------------------

class FakeFred:
    """Stands in for FRED: answers in order, records every address asked for. No network is used."""

    def __init__(self, *answers):
        self.answers, self.urls = list(answers), []

    def get(self, url):
        self.urls.append(url)
        found = self.answers.pop(0)
        if isinstance(found, Exception):
            raise found
        return found


class Clock:
    def __init__(self):
        self.t, self.slept = 1000.0, []

    def __call__(self):
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += seconds


def client(fake, now=READ):
    clock = Clock()
    return news_fetch.FredClient(KEY, get=fake.get, sleep=clock.sleep, clock=clock, now=lambda: now), clock


def first_fetch(env, extra=()):
    c, load, ask, describe, tmp_path = env
    fake = FakeFred((200, answer(rows(DGS10), ask("DGS10"))), (200, describe("DGS10")), *extra)
    fred, clock = client(fake)
    report = news_fetch.fetch_macro_series(c, fred, "DGS10", tmp_path / "fetched", raw_dir=tmp_path / "raw")
    return report, fake, fred, clock


def everything_stored(c, tmp_path):
    texts = []
    for (table,) in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
        texts += [repr(row) for row in c.execute(f"SELECT * FROM {table}")]
    texts += [p.read_bytes().decode("utf-8", "replace") for p in tmp_path.rglob("*") if p.is_file()]
    return "\n".join(texts)


def test_the_key_comes_only_from_the_environment_and_is_never_shown():
    assert news_fetch.fred_key({"FRED_API_KEY": f"  {KEY} "}) == KEY
    for environ in ({}, {"FRED_API_KEY": ""}, {"FRED_API_KEY": KEY.upper()}, {"FRED_API_KEY": KEY + "0"}):
        with pytest.raises(news_fetch.FetchError, match="FRED_API_KEY is not set") as raised:
            news_fetch.fred_key(environ)
        assert KEY not in str(raised.value) and KEY.upper() not in str(raised.value)


def test_a_fetch_asks_for_the_observations_then_the_description(env):
    c, *_, tmp_path = env
    report, fake, fred, _ = first_fetch(env)
    assert report["vintages_recorded"] == 7 and fred.requests == 2
    first, second = (news_fetch.urllib.parse.urlsplit(u) for u in fake.urls)
    assert (first.scheme, first.netloc, first.path) == ("https", "api.stlouisfed.org", "/fred/series/observations")
    assert news_fetch.urllib.parse.parse_qs(first.query) == {
        "series_id": ["DGS10"], "observation_start": ["2016-01-01"], "realtime_start": ["2023-10-04"],
        "realtime_end": ["9999-12-31"], "file_type": ["json"], "api_key": [KEY]}
    assert second.path == "/fred/series" and news_fetch.urllib.parse.parse_qs(second.query) == {
        "series_id": ["DGS10"], "file_type": ["json"], "api_key": [KEY]}
    names = sorted(p.name for p in (tmp_path / "fetched").iterdir())
    assert names == ["fred_DGS10_20261003143900_observations.json", "fred_DGS10_20261003143900_series.json"]


def test_the_key_never_reaches_the_database_files_or_messages(env):
    c, *_, tmp_path = env
    first_fetch(env)
    assert KEY not in everything_stored(c, tmp_path)


def test_requests_are_spaced_as_fred_asks(env):
    _, _, _, clock = first_fetch(env)
    assert clock.slept == [news_fetch.FRED_INTERVAL]


@pytest.mark.parametrize("failure, error, message", [
    ((400, b'{"error_code":400,"error_message":"Bad Request.  The series does not exist."}'), news_fetch.FetchError,
     "HTTP 400: Bad Request.  The series does not exist."),
    ((500, b"<html>oops</html>"), news_fetch.FetchError, "HTTP 500: no readable message"),
    ((200, b'{"echo": "' + KEY.encode() + b'"}'), news_fetch.FetchError, "contained the key"),
    ((429, b"Too Many Requests"), news_fetch.RateLimited, "HTTP 429"),
    (ValueError(f"bad address https://api.stlouisfed.org/fred/series/observations?api_key={KEY}"),
     news_fetch.FetchError, "FRED could not be asked: bad address .*api_key=<key>"),
    ((200, b"<html>maintenance</html>"), MacroResponseError, "Not FRED's JSON"),
])
def test_a_failed_request_stores_nothing_and_never_shows_the_key(env, failure, error, message):
    c, _, _, _, tmp_path = env
    fred, _ = client(FakeFred(failure))
    with pytest.raises(error, match=message) as raised:
        news_fetch.fetch_macro_series(c, fred, "DGS10", tmp_path / "fetched", raw_dir=tmp_path / "raw")
    assert KEY not in str(raised.value)
    assert count(c, "raw_artifacts") == 0 and not (tmp_path / "fetched").exists()
    assert fred.requests == 1    # the description is never asked for after a refused answer


def test_fred_is_not_asked_again_in_a_run_after_it_said_slow_down(env):
    c, _, _, _, tmp_path = env
    fake = FakeFred((429, b"Too Many Requests"))
    fred, _ = client(fake)
    for _ in range(2):
        with pytest.raises(news_fetch.RateLimited):
            news_fetch.fetch_macro_series(c, fred, "DGS10", tmp_path / "f", raw_dir=tmp_path / "raw")
    assert len(fake.urls) == 1


def test_a_refused_description_stores_nothing(env):
    c, _, ask, describe, tmp_path = env
    fred, _ = client(FakeFred((200, answer(rows(DGS10), ask("DGS10"))), (200, describe("DGS10", units="Basis Points"))))
    with pytest.raises(MacroResponseError, match="units"):
        news_fetch.fetch_macro_series(c, fred, "DGS10", tmp_path / "f", raw_dir=tmp_path / "raw")
    assert count(c, "raw_artifacts") == 0 and not (tmp_path / "f").exists()


def test_a_later_fetch_asks_only_for_recent_dates(env):
    c, _, ask, describe, tmp_path = env
    first_fetch(env)
    recent = ask("DGS10", start="2026-08-17", realtime_start="2023-10-05")   # 45 days back; the window moves too
    fake = FakeFred((200, answer(rows(DGS10[-2:]), recent)), (200, describe("DGS10")))
    fred, _ = client(fake, now=READ + timedelta(days=1))
    report = news_fetch.fetch_macro_series(c, fred, "DGS10", tmp_path / "fetched", raw_dir=tmp_path / "raw")
    assert "observation_start=2026-08-17" in fake.urls[0] and "realtime_start=2023-10-05" in fake.urls[0]
    assert (report["vintages_recorded"], report["already_present"]) == (0, 2)


def test_the_same_answer_fetched_again_is_reported_as_nothing_new(env):
    c, _, ask, describe, tmp_path = env
    first_fetch(env)
    fred, _ = client(FakeFred((200, answer(rows(DGS10), ask("DGS10"))), (200, describe("DGS10"))))
    report = news_fetch.fetch_macro_series(c, fred, "DGS10", tmp_path / "fetched", raw_dir=tmp_path / "raw",
                                           full=True)
    assert report["note"].startswith("identical") and count(c, "mc_responses") == 1


def test_the_fetcher_asks_fred_for_nothing_but_series_and_observations():
    for url in ("https://api.stlouisfed.org/fred/series/search?search_text=india",
                "https://api.stlouisfed.org/fred/category/series?category_id=1",
                "https://api.stlouisfed.org:8443/fred/series?series_id=DGS10"):
        with pytest.raises(news_fetch.FetchError, match="not an allowed address"):
            news_fetch.http_get(url)
    for url in ("https://fred.stlouisfed.org/series/DGS10", "https://alfred.stlouisfed.org/series?seid=DGS10",
                "http://api.stlouisfed.org/fred/series?series_id=DGS10"):
        with pytest.raises(news_fetch.FetchError, match="not an allowed host"):
            news_fetch.http_get(url)
    with pytest.raises(news_fetch.FetchError) as raised:
        news_fetch.http_get(f"https://api.stlouisfed.org/fred/series/search?api_key={KEY}")
    assert KEY not in str(raised.value)


# ---- static rules (40D, 3G rule 2, 4G rule 5) -------------------------------------------------------------

def test_only_the_network_module_reads_the_environment():
    pattern = re.compile(r"\bos\.environ\b|\bgetenv\b|^\s*from\s+os\s+import", re.M)
    files = list((PROJECT_ROOT / "src").rglob("*.py")) + [PROJECT_ROOT / "manage.py"]
    readers = [p.name for p in files if pattern.search(p.read_text(encoding="utf-8"))]
    assert readers == ["news_fetch.py"]


def test_macro_context_is_never_a_target_benchmark_or_ledger_input():
    # 3G rule 2: foreign indices, yields and prices are never covered securities, targets or benchmarks.
    uses = re.compile(r"^\s*(from\s+ingestion\.macro_context\s+import|import\s+ingestion\.macro_context)", re.M)
    guarded = [p for d in ("targets", "ledger", "calibration", "validation", "models", "universe")
               for p in (PROJECT_ROOT / "src" / d).rglob("*.py")]
    assert [str(p) for p in guarded if uses.search(p.read_text(encoding="utf-8"))] == []


def test_the_fred_notice_is_shown():
    assert FRED_NOTICE == ("This product uses the FRED\u00ae API but is not endorsed or certified by the Federal"
                           " Reserve Bank of St. Louis.")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "This product uses the FRED&reg; API but is not endorsed or certified by the Federal Reserve" in readme
    assert (PROJECT_ROOT / "manage.py").read_text(encoding="utf-8").count("FRED_NOTICE") >= 3


# ---- registry, migration and acceptance record ------------------------------------------------------------

def test_fred_is_registered_with_its_terms(env):
    c, *_ = env
    source = get_source(c, "fred_alfred")
    assert source["source_class"] == "official_statistics" and source["authority"] == "secondary"
    for words in ("personal use", "S&P Dow Jones Indices series refused", "never redistributed", "never stored"):
        assert words in source["license"]


def test_macro_tables_are_append_only(env):
    c, load, *_ = env
    load("DGS10", DGS10)
    c.execute("INSERT INTO mc_problems VALUES (1, 'x', 'x')")
    for sql in ("UPDATE mc_vintages SET value = 0", "DELETE FROM mc_vintages", "UPDATE mc_series SET title = 'x'",
                "DELETE FROM mc_series", "UPDATE mc_responses SET rows = 0", "DELETE FROM mc_responses",
                "UPDATE mc_problems SET kind = 'y'", "DELETE FROM mc_problems"):
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            c.execute(sql)


def test_the_macro_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 16)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not [n for n in names if n.startswith("mc_")] and "sb_releases" in names
    c.close()


def test_stage_10c_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_10C_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_MACRO_CONTEXT_BASELINE"
    assert record["negative_assertions"]["foreign close available to an Indian decision before its session ended"] \
        is False
    assert record["negative_assertions"]["FRED key in the repository, database, files, logs or messages"] is False
