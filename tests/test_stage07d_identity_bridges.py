"""Stage 7D tests: identity bridges - ISIN is not permanently stable (architecture 6D).

Found on real NSE data: TAALTECH traded as INE524T01011 until 21-Sep-2026 and as
INE524T01029 from its split on 22-Sep-2026. A bridge is created only with all
6D evidence; it is scoped to one corporate-action event; it never makes two
ISINs interchangeable; raw rows keep their own ISIN. Without a bridge, an
adjusted window across the split fails closed instead of being shortened.
"""
import csv
import io
import sqlite3

import pytest

from core.config import PROJECT_ROOT
from core.database import connect, migrate, rollback
from features.price_series import AdjustmentBlocked, adjusted_series, raw_series
from ingestion.market_adapters import AdapterError, ingest_market_file, retry_quarantined
from ingestion.nse_corporate_actions import load_corporate_actions
from ingestion.source_registry import sync_sources
from universe.entities import add_alias, resolve, validate_isin
from universe.equity_list import load_equity_list
from universe.identity_bridges import BridgeRefused, create_bridge

RETRIEVED = "2026-10-02T15:00:00+05:30"


def make_isin(base):
    for digit in "0123456789":
        try:
            return validate_isin(base + digit)
        except Exception:
            continue


OLD, NEW, OTHER, STRAY = make_isin("INE200A0101"), make_isin("INE200A0102"), make_isin("INE201A0101"), make_isin("INE202A0101")

UDIFF = ["TradDt", "ISIN", "TckrSymb", "SctySrs", "FinInstrmTp", "FinInstrmNm", "OpnPric", "HghPric", "LwPric",
         "ClsPric", "TtlTradgVol"]
LEGACY = ["SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY", "TIMESTAMP", "ISIN"]


def udiff(rows):
    """rows: (date, isin, symbol, name, close)"""
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(UDIFF)
    for d, isin, sym, name, close in rows:
        w.writerow([d, isin, sym, "EQ", "STK", name, close, close, close, close, "1000"])
    return out.getvalue()


def legacy(rows):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(LEGACY)
    months = {"09": "SEP"}
    for d, isin, sym, _, close in rows:
        y, m, dd = d.split("-")
        w.writerow([sym, "EQ", close, close, close, close, "1000", f"{dd}-{months[m]}-{y}", isin])
    return out.getvalue()


EQUITY_LIST = ("SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n"
               f"SPLITCO,Split Co Limited,EQ,01-JAN-2010,2,1,{NEW},2\n"
               f"OTHERCO,Other Co Limited,EQ,01-JAN-2010,1,1,{OTHER},1\n")
CA_FILE = ('\ufeff"SYMBOL","COMPANY NAME","SERIES","PURPOSE","FACE VALUE","EX-DATE","RECORD DATE",'
           '"BOOK CLOSURE START DATE","BOOK CLOSURE END DATE"\n'
           '"SPLITCO","Split Co Limited","EQ","Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- '
           'Per Share","2","22-Sep-2026","22-Sep-2026","-","-"\n')
DAY1 = [("2026-09-21", OLD, "SPLITCO", "SPLIT CO LTD.", "5000.00"), ("2026-09-21", OTHER, "OTHERCO", "OTHER CO LTD", "100.00")]
DAY2 = [("2026-09-22", NEW, "SPLITCO", "SPLIT CO LTD.", "1010.00"), ("2026-09-22", OTHER, "OTHERCO", "OTHER CO LTD", "101.00")]


@pytest.fixture
def setup(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    files = {}

    def put(name, text):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return path

    def ingest(name, text):
        return ingest_market_file(c, put(name, text), RETRIEVED, raw_dir=tmp_path / "raw")

    load_equity_list(c, put("EQUITY_L.csv", EQUITY_LIST), RETRIEVED, raw_dir=tmp_path / "raw")
    files["put"], files["ingest"], files["raw"] = put, ingest, tmp_path / "raw"
    yield c, files
    c.close()


def standard(c, f, day1=DAY1, day2=DAY2, fmt=udiff, with_split=True):
    r1 = f["ingest"]("day1.csv", fmt(day1))
    f["ingest"]("day2.csv", fmt(day2))
    if with_split:
        load_corporate_actions(c, f["put"]("ca.csv", CA_FILE), RETRIEVED, raw_dir=f["raw"])
    return r1["artifact_id"]


# ---- the real TAALTECH case ----

def test_without_a_bridge_the_window_fails_closed_not_shortened(setup):
    c, f = setup
    standard(c, f)
    with pytest.raises(AdjustmentBlocked, match="identity bridge is needed"):
        adjusted_series(c, NEW, "2026-09-21", "2026-09-22")


def test_a_bridge_joins_the_two_isins_for_that_event_only(setup):
    c, f = setup
    day1_artifact = standard(c, f)
    bridge = create_bridge(c, "SPLITCO", "2026-09-22")
    assert (bridge["old_isin"], bridge["new_isin"], bridge["last_old_date"]) == (OLD, NEW, "2026-09-21")

    retried = retry_quarantined(c, day1_artifact, "bridge recorded", only_isins={OLD})
    assert (retried["rows_retried"], retried["rows_trusted"]) == (1, 1)

    adjusted = adjusted_series(c, NEW, "2026-09-21", "2026-09-22")
    assert adjusted.closes() == pytest.approx([1000.0, 1010.0])             # continuous across the split
    assert adjusted.row_isins == (OLD, NEW) and adjusted.bridges_used == (bridge["bridge_id"],)
    bridged_raw = raw_series(c, NEW, "2026-09-21", "2026-09-22", follow_bridges=True)
    assert bridged_raw.closes() == [5000.0, 1010.0]                         # the raw jump is still visible
    assert raw_series(c, NEW, "2026-09-21", "2026-09-22").closes() == [1010.0]  # strict raw: one ISIN only


def test_a_bridge_never_makes_isins_interchangeable(setup):
    c, f = setup
    standard(c, f)
    create_bridge(c, "SPLITCO", "2026-09-22")
    assert resolve(c, OLD, "2026-09-21") == OLD and resolve(c, NEW, "2026-09-22") == NEW
    assert c.execute("SELECT trade_date FROM trusted_prices WHERE isin = ?", [NEW]).fetchall() == [("2026-09-22",)]
    event = c.execute("SELECT isin, related_isin, effective_date FROM entity_events WHERE event_type = 'isin_change'").fetchone()
    assert event == (OLD, NEW, "2026-09-22")


def test_the_old_isin_is_accepted_only_before_the_ex_date_and_only_for_that_symbol(setup):
    c, f = setup
    standard(c, f)
    create_bridge(c, "SPLITCO", "2026-09-22")
    late = f["ingest"]("late.csv", udiff([("2026-09-23", OLD, "SPLITCO", "SPLIT CO LTD.", "1000.00")]))
    other_symbol = f["ingest"]("othersym.csv", udiff([("2026-09-18", OLD, "OTHERCO", "SPLIT CO LTD.", "4900.00")]))
    assert late["rows_quarantined"] == 1 and other_symbol["rows_quarantined"] == 1
    before = f["ingest"]("before.csv", udiff([("2026-09-18", OLD, "SPLITCO", "SPLIT CO LTD.", "4900.00")]))
    assert before["rows_trusted"] == 1


def test_the_bridge_is_tied_to_its_symbol_even_for_the_same_company(setup):
    c, f = setup
    standard(c, f)
    create_bridge(c, "SPLITCO", "2026-09-22")
    add_alias(c, NEW, "nse_symbol", "SPLITX", "2010-01-01")  # a second symbol for the same company
    report = f["ingest"]("splitx.csv", udiff([("2026-09-18", OLD, "SPLITX", "SPLIT CO LTD.", "4900.00")]))
    assert report["rows_quarantined"] == 1                    # no symbol-free bridging


# ---- refusals: no bridge without the full 6D evidence; nothing written ----

def assert_nothing_written(c):
    assert c.execute("SELECT COUNT(*) FROM identity_bridges").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM entities WHERE isin = ?", [OLD]).fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM entity_events WHERE event_type = 'isin_change'").fetchone()[0] == 0


def test_no_bridge_when_names_differ(setup):
    c, f = setup
    day1 = [("2026-09-21", OLD, "SPLITCO", "SOMEONE ELSE LTD", "5000.00")]
    standard(c, f, day1=day1)
    with pytest.raises(BridgeRefused, match="names differ"):
        create_bridge(c, "SPLITCO", "2026-09-22")
    assert_nothing_written(c)


def test_no_bridge_without_a_recorded_split_or_bonus(setup):
    c, f = setup
    standard(c, f, with_split=False)
    with pytest.raises(BridgeRefused, match="no split or bonus"):
        create_bridge(c, "SPLITCO", "2026-09-22")
    assert_nothing_written(c)


def test_no_bridge_when_the_symbol_shows_two_isins(setup):
    c, f = setup
    day1 = DAY1 + [("2026-09-21", STRAY, "SPLITCO", "SPLIT CO LTD.", "4999.00")]
    standard(c, f, day1=day1)
    with pytest.raises(BridgeRefused, match="exactly one ISIN"):
        create_bridge(c, "SPLITCO", "2026-09-22")
    assert_nothing_written(c)


def test_no_bridge_when_the_file_format_has_no_name_column(setup):
    c, f = setup
    standard(c, f, fmt=legacy)
    with pytest.raises(BridgeRefused, match="no security-name column"):
        create_bridge(c, "SPLITCO", "2026-09-22")
    assert_nothing_written(c)


def test_no_bridge_when_the_isin_did_not_change(setup):
    c, f = setup
    day1 = [("2026-09-21", NEW, "SPLITCO", "SPLIT CO LTD.", "5000.00")]
    standard(c, f, day1=day1)
    with pytest.raises(BridgeRefused, match="no ISIN change"):
        create_bridge(c, "SPLITCO", "2026-09-22")


def test_a_bridge_is_made_once_and_never_changed(setup):
    c, f = setup
    standard(c, f)
    create_bridge(c, "SPLITCO", "2026-09-22")
    with pytest.raises(BridgeRefused, match="already bridged"):
        create_bridge(c, "SPLITCO", "2026-09-22")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        c.execute("UPDATE identity_bridges SET old_isin = new_isin")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        c.execute("DELETE FROM identity_bridges")


# ---- retries ----

def test_retry_touches_only_the_rows_asked_for(setup):
    c, f = setup
    day1 = DAY1 + [("2026-09-21", STRAY, "STRAYCO", "STRAY LTD", "10.00")]
    day1_artifact = standard(c, f, day1=day1)
    create_bridge(c, "SPLITCO", "2026-09-22")
    retried = retry_quarantined(c, day1_artifact, "bridge recorded", only_isins={OLD})
    assert retried["rows_retried"] == 1                          # STRAYCO is left alone
    assert retry_quarantined(c, day1_artifact, "again", only_isins={OLD})["rows_retried"] == 0
    with pytest.raises(AdapterError, match="reason"):
        retry_quarantined(c, day1_artifact, " ")


# ---- static checks, migration, acceptance record ----

def test_bridges_can_never_create_adjustment_factors():
    text = (PROJECT_ROOT / "src" / "universe" / "identity_bridges.py").read_text(encoding="utf-8")
    assert "record_action" not in text and "INSERT INTO corporate_actions" not in text and "close_price" not in text


def test_bridge_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 9)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not {"identity_bridges", "retry_runs"} & names and "ca_file_loads" in names
    c.close()


def test_stage_7d_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record_ = load_acceptance_records()["STAGE_07D_acceptance.yaml"]
    assert record_["status"] == "ACCEPTED_IDENTITY_BRIDGE_BASELINE"
    assert record_["negative_assertions"]["global ISIN equivalence created"] is False
