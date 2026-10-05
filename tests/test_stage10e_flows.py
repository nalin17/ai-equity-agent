"""Stage 10E tests: aggregate investor flows - NSE's daily FII/FPI and DII trading activity (architecture 40B
step 9c, 3C rule 1, 3G, 4, 4C, 5B; ADR-004, ADR-011).

Built on NSE's real files for 01-Oct-2026, downloaded by the owner on 04-Oct-2026 from
nseindia.com/reports/fii-dii: fii-dii-nse-latest.csv (DII buy 24,077.65, sell 14,444.02, net 9,633.63;
FII/FPI buy 11,210.36, sell 20,370.35, net -9,159.99) and fii-dii-combined-latest.csv (DII net 10,041.84,
FII/FPI net -9,484.22), Rs crore - with their byte-order mark, header cells split over two lines and the rupee
sign. Figures for other days are made up.
"""
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from core.config import PROJECT_ROOT
from core.database import connect, migrate, rollback
from data_quality.missing_data import MissingClass
from data_quality.trust_chain import NoDataError
from ingestion.intake import REUSED_NAMES, collect_downloads, ingest_inbox, kind_of
from ingestion.nse_flows import (CATEGORIES, HEADER, STATUS, UNIT, FlowsFileError, flows, load_flows, missing_days,
                                 read_flows, scope_of)
from ingestion.source_registry import get_source, sync_sources
from provenance.availability import PitClaim
from provenance.raw_store import ArtifactError

UTC = timezone.utc
CURRENT, REPLAY = PitClaim.CURRENT_DECISION, PitClaim.HISTORICAL_REPLAY
READ = datetime(2026, 10, 4, 17, 39, tzinfo=UTC)      # 23:09 India time, when the owner downloaded the files
AFTER = READ + timedelta(minutes=5)
RUPEE = chr(0x20B9)
BOM = chr(0xFEFF)
REAL_HEADER = ('"CATEGORY \n","DATE \n","BUY VALUE \n(' + RUPEE + ' Crores)","SELL VALUE \n(' + RUPEE
               + ' Crores)","NET VALUE \n(' + RUPEE + ' Crores)"')
NSE = [("DII", "01-Oct-2026", "24,077.65", "14,444.02", "9,633.63"),
       ("FII/FPI", "01-Oct-2026", "11,210.36", "20,370.35", "-9,159.99")]          # real
COMBINED = [("DII", "01-Oct-2026", "25,420.04", "15,378.20", "10,041.84"),
            ("FII/FPI", "01-Oct-2026", "12,260.26", "21,744.48", "-9,484.22")]     # real


def text(rows, header=REAL_HEADER, bom=True, end=""):
    body = "\n".join(",".join(f'"{v}"' for v in row) for row in rows)
    return (BOM if bom else "") + header + "\n" + body + end


@pytest.fixture
def env(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    folders = iter(range(1000))

    def write(rows, name="fii-dii-nse-latest.csv", **kw):
        folder = tmp_path / f"f{next(folders)}"
        folder.mkdir()
        path = folder / name
        path.write_bytes(text(rows, **kw).encode("utf-8"))
        return path

    def load(rows, name="fii-dii-nse-latest.csv", read=READ, **kw):
        return load_flows(c, write(rows, name, **kw), read, raw_dir=tmp_path / "raw")

    yield c, write, load, tmp_path
    c.close()


def count(c, table):
    return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def nets(c, when=AFTER, claim=CURRENT, scope="nse"):
    return {(r["trade_date"], r["category"]): r["net_crore"] for r in flows(c, when, claim, scope)}


# ---- reading and storing NSE's real files ---------------------------------------------------------

def test_a_real_nse_file_is_kept_and_its_figures_stored(env):
    c, _, load, _ = env
    report = load(NSE)
    assert report == {"file_id": 1, "scope": "nse", "trade_date": "2026-10-01", "values_recorded": 2,
                      "already_present": 0, "revised": 0, "fii_fpi_net_crore": "-9159.99", "dii_net_crore": "9633.63"}
    assert c.execute("SELECT source_id, original_name FROM raw_artifacts").fetchall() == [
        ("nse_fii_dii", "fii-dii-nse-latest.csv")]
    rows = flows(c, AFTER, CURRENT)
    assert [(r["category"], r["buy_crore"], r["sell_crore"], r["net_crore"]) for r in rows] == [
        ("DII", 24077.65, 14444.02, 9633.63), ("FII/FPI", 11210.36, 20370.35, -9159.99)]
    assert {(r["status"], r["unit"], r["known_from"]) for r in rows} == {(STATUS, UNIT, READ.isoformat())}
    assert rows[1]["value_text"] == "11,210.36 | 20,370.35 | -9,159.99"


def test_the_combined_file_is_its_own_scope(env):
    c, _, load, _ = env
    load(NSE)
    load(COMBINED, name="fii-dii-combined-latest.csv")
    assert nets(c, scope="nse_bse_msei") == {("2026-10-01", "DII"): 10041.84, ("2026-10-01", "FII/FPI"): -9484.22}
    assert nets(c)[("2026-10-01", "DII")] == 9633.63
    assert scope_of("fii-dii-combined-latest__1a2b3c4d.csv") == "nse_bse_msei" and scope_of("fii-dii.csv") is None


def test_the_header_is_read_through_its_line_breaks_and_rupee_sign(env):
    _, write, _, _ = env
    scope, day, found = read_flows(write(NSE), READ)
    assert (scope, day, sorted(found)) == ("nse", "2026-10-01", sorted(CATEGORIES))
    assert HEADER[2] == "BUY VALUE (" + RUPEE + " Crores)"
    assert read_flows(write(NSE, bom=False, end="\n"), READ)[1] == "2026-10-01"


def test_indian_digit_grouping_is_read(env):
    c, _, load, _ = env
    load([("DII", "01-Oct-2026", "1,25,420.04", "15,378.20", "1,10,041.84"), NSE[1]])
    assert nets(c)[("2026-10-01", "DII")] == 110041.84


# ---- 40B step 9c: stamped with publication (ingestion) time, never the trade date -----------------

def test_a_flow_is_known_from_ingestion_never_from_its_trade_date(env):
    c, _, load, _ = env
    load(NSE)
    close_of_trade = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)   # 15:30 India time on the trade date
    for when in (close_of_trade, datetime(2026, 10, 2, tzinfo=UTC), READ - timedelta(seconds=1)):
        assert flows(c, when, CURRENT) == []
    assert len(flows(c, READ, CURRENT)) == 2


def test_flows_never_support_historical_replay(env):
    c, _, load, _ = env
    load(NSE)
    assert flows(c, AFTER + timedelta(days=30), REPLAY) == []   # no publication time (AVAILABILITY_REVIEW)


def test_the_same_day_with_other_figures_is_a_new_vintage(env):
    c, _, load, _ = env
    load(NSE)
    later = READ + timedelta(days=1)
    changed = [NSE[0], ("FII/FPI", "01-Oct-2026", "11,210.36", "20,380.35", "-9,169.99")]
    report = load(changed, read=later)
    assert (report["values_recorded"], report["already_present"], report["revised"]) == (1, 1, 1)
    assert nets(c, AFTER)[("2026-10-01", "FII/FPI")] == -9159.99           # as known before the second file
    assert nets(c, later + timedelta(minutes=1))[("2026-10-01", "FII/FPI")] == -9169.99
    assert count(c, "fl_flows") == 3
    again = load(changed, read=later + timedelta(hours=1), end="\n")   # the revised figures once more
    assert (again["values_recorded"], again["already_present"], again["revised"]) == (0, 2, 0)


def test_flows_can_be_chosen_by_trade_date(env):
    c, _, load, _ = env
    load(NSE)
    assert flows(c, AFTER, CURRENT, "nse", start="2026-10-02") == []
    assert flows(c, AFTER, CURRENT, "nse", end="2026-09-30") == []
    assert len(flows(c, AFTER, CURRENT, "nse", start="2026-10-01", end="2026-10-01")) == 2


def test_the_same_figures_again_store_nothing_new(env):
    c, _, load, _ = env
    load(NSE)
    report = load(NSE, read=READ + timedelta(hours=1), end="\n")        # other bytes, same figures
    assert (report["values_recorded"], report["already_present"], report["revised"]) == (0, 2, 0)
    assert count(c, "fl_flows") == 2 and count(c, "fl_files") == 2


def test_an_identical_file_is_already_stored(env):
    c, write, _, tmp_path = env
    path = write(NSE)
    load_flows(c, path, READ, raw_dir=tmp_path / "raw")
    with pytest.raises(ArtifactError):
        load_flows(c, path, AFTER, raw_dir=tmp_path / "raw")


# ---- files that cannot be used are refused whole ---------------------------------------------------

LAKH_HEADER = REAL_HEADER.replace("Crores", "Lakhs")


@pytest.mark.parametrize("rows, kw, error, message", [
    (NSE, {"header": LAKH_HEADER}, FlowsFileError, "not NSE's FII/DII table in crore"),
    (NSE, {"header": REAL_HEADER + ',"REMARKS"'}, FlowsFileError, "not NSE's FII/DII table"),
    (NSE, {"header": REAL_HEADER.rsplit(",", 1)[0]}, FlowsFileError, "not NSE's FII/DII table"),
    ([], {}, NoDataError, "no rows"),
    (NSE[:1], {}, FlowsFileError, "1 rows"),
    (NSE + [("PRO", "01-Oct-2026", "1.00", "1.00", "0.00")], {}, FlowsFileError, "3 rows"),
    ([("PRO", "01-Oct-2026", "1.00", "1.00", "0.00"), NSE[1]], {}, FlowsFileError, "unknown or repeated"),
    ([NSE[1], NSE[1]], {}, FlowsFileError, "unknown or repeated"),
    ([NSE[0], ("FII/FPI", "30-Sep-2026", "11,210.36", "20,370.35", "-9,159.99")], {}, FlowsFileError, "different days"),
    ([("DII", "2026-10-01", "24,077.65", "14,444.02", "9,633.63"), NSE[1]], {}, FlowsFileError, "not like 01-Oct-2026"),
    ([("DII", "01-Oct-2026", "24077.65", "14,444.02", "9,633.63"), NSE[1]], {}, FlowsFileError, "not an amount"),
    ([("DII", "01-Oct-2026", "24,077.6", "14,444.02", "9,633.58"), NSE[1]], {}, FlowsFileError, "not an amount"),
    ([("DII", "01-Oct-2026", "", "14,444.02", "9,633.63"), NSE[1]], {}, FlowsFileError, "not an amount"),
    ([("DII", "01-Oct-2026", "-1,000.00", "1,000.00", "-2,000.00"), NSE[1]], {}, FlowsFileError, "negative"),
    ([("DII", "01-Oct-2026", "24,077.65", "14,444.02", "9,633.64"), NSE[1]], {}, FlowsFileError, "minus sell"),
    ([(r[0], "02-Oct-2026") + r[2:] for r in NSE], {}, FlowsFileError, "not an NSE trading day"),   # Gandhi Jayanti
    ([(r[0], "03-Oct-2026") + r[2:] for r in NSE], {}, FlowsFileError, "not an NSE trading day"),   # a Saturday
    ([(r[0], "05-Oct-2026") + r[2:] for r in NSE], {}, FlowsFileError, "after the file was ingested"),
    ([(r[0], "04-Jan-2027") + r[2:] for r in NSE], {}, FlowsFileError, "does not cover"),
])
def test_a_file_that_cannot_be_used_is_refused_whole_and_nothing_stored(env, rows, kw, error, message):
    c, _, load, _ = env
    read = datetime(2027, 1, 5, tzinfo=UTC) if "Jan-2027" in str(rows) else READ
    with pytest.raises(error, match=message):
        load(rows, read=read, **kw)
    assert count(c, "raw_artifacts") == count(c, "fl_files") == count(c, "fl_flows") == 0


def test_an_unknown_file_name_is_refused(env):
    _, write, _, _ = env
    with pytest.raises(FlowsFileError, match="not an NSE FII/DII file name"):
        read_flows(write(NSE, name="fii-dii-bse-latest.csv"), READ)


# ---- missing trading days (4C) --------------------------------------------------------------------

def test_trading_days_without_a_file_are_reported_missing_never_filled(env):
    c, _, load, _ = env
    load(NSE)
    gaps = missing_days(c, AFTER, CURRENT, "nse", "2026-09-28", "2026-10-04")
    assert [g["trade_date"] for g in gaps] == ["2026-09-28", "2026-09-29", "2026-09-30"]   # 02-Oct holiday, weekend
    assert {g["missing_class"] for g in gaps} == {MissingClass.EXTRACTION_FAILURE}
    assert nets(c) == {("2026-10-01", "DII"): 9633.63, ("2026-10-01", "FII/FPI"): -9159.99}   # nothing filled
    assert [g["trade_date"] for g in missing_days(c, READ - timedelta(seconds=1), CURRENT, "nse", "2026-10-01",
                                                  "2026-10-01")] == ["2026-10-01"]   # not ingested yet then
    assert [g["trade_date"] for g in missing_days(c, AFTER, CURRENT, "nse", "2026-12-31", "2027-01-08")] == [
        "2026-12-31"]   # a trading day; beyond the calendar nothing is claimed


# ---- the intake (ADR-004) -------------------------------------------------------------------------

def test_the_intake_keeps_each_days_download_and_loads_them_in_download_order(env):
    c, _, _, tmp_path = env
    downloads, inbox = tmp_path / "downloads", tmp_path / "inbox"
    downloads.mkdir()
    first = downloads / "fii-dii-nse-latest.csv"
    first.write_bytes(text(NSE).encode("utf-8"))
    os.utime(first, (1_000_000_000, 1_000_000_000))
    assert collect_downloads(downloads, inbox)["moved"] == ["fii-dii-nse-latest.csv"]
    revised = [NSE[0], ("FII/FPI", "01-Oct-2026", "11,210.36", "20,380.35", "-9,169.99")]
    second = downloads / "fii-dii-nse-latest (1).csv"          # the browser's name for a repeated download
    second.write_bytes(text(revised).encode("utf-8"))
    moved = collect_downloads(downloads, inbox)["moved"]
    assert len(moved) == 1 and re.fullmatch(r"fii-dii-nse-latest__[0-9a-f]{8}\.csv", moved[0])
    assert "flows" in REUSED_NAMES and kind_of(moved[0])[0] == "flows"
    os.utime(inbox / moved[0], (2_000_000_000, 2_000_000_000))
    results = ingest_inbox(c, inbox, raw_dir=tmp_path / "raw", now=lambda: READ)
    assert [(name, outcome) for name, _, outcome, _ in results] == [("fii-dii-nse-latest.csv", "loaded"),
                                                                     (moved[0], "loaded")]
    assert nets(c)[("2026-10-01", "FII/FPI")] == -9169.99      # the later download is the latest vintage


def test_a_refused_flow_file_is_reported_by_the_intake(env):
    c, _, _, tmp_path = env
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "fii-dii-nse-latest.csv").write_bytes(text([NSE[0], ("FII/FPI", "01-Oct-2026", "1.00", "2.00",
                                                                  "3.00")]).encode("utf-8"))
    [(name, kind, outcome, detail)] = ingest_inbox(c, inbox, raw_dir=tmp_path / "raw", now=lambda: READ)
    assert (kind, outcome) == ("flows", "failed") and "minus sell" in detail
    assert count(c, "fl_files") == 0


# ---- static rules, registry, migration and acceptance record ---------------------------------------

def test_flows_never_feed_targets_benchmarks_or_ledgers():
    uses = re.compile(r"^\s*(from\s+ingestion\.nse_flows\s+import|import\s+ingestion\.nse_flows)", re.M)
    guarded = [p for d in ("targets", "ledger", "calibration", "validation", "models", "universe")
               for p in (PROJECT_ROOT / "src" / d).rglob("*.py")]
    assert [str(p) for p in guarded if uses.search(p.read_text(encoding="utf-8"))] == []


def test_nse_fii_dii_is_registered_with_its_terms(env):
    c, *_ = env
    source = get_source(c, "nse_fii_dii")
    assert source["source_class"] == "exchange_official" and source["authority"] == "primary"
    for words in ("no automated collection", "downloaded by hand", "never redistributed", "NSDL and CDSL"):
        assert words in source["license"]


def test_flow_tables_are_append_only(env):
    c, _, load, _ = env
    load(NSE)
    for sql in ("UPDATE fl_files SET recorded = 0", "DELETE FROM fl_files", "UPDATE fl_flows SET net_crore = 0",
                "DELETE FROM fl_flows"):
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            c.execute(sql)


def test_the_flows_migration_rolls_back_cleanly():
    c = connect(":memory:")
    assert migrate(c) >= 20
    rollback(c, 19)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not [n for n in names if n.startswith("fl_")] and "me_routes" in names
    c.close()


def test_stage_10e_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_10E_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_INVESTOR_FLOWS_BASELINE"
    assert record["negative_assertions"]["flow stamped with its trade date as its availability"] is False
    assert record["negative_assertions"]["NSDL or CDSL data stored"] is False
