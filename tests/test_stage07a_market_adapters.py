"""Stage 7A acceptance tests: NSE market data adapters and the equity list.

40A item 7 / 40B step 6: a provider is swapped behind the interface with no
downstream file change.
40G.2: an unrecognised format fails loudly; checks are never loosened.
Adapters translate, never repair: untranslatable values reach the trust chain
unchanged and are quarantined, kept exactly as received.
The equity list is a current snapshot: it never overwrites a known company,
and differences are rejected and recorded, not guessed.
"""
import csv
import dataclasses
import hashlib
import io
import json
import re
import zipfile

import pytest

import universe.equity_list as equity_list
from core.config import PROJECT_ROOT
from core.database import connect, migrate, rollback
from data_quality.trust_chain import NoDataError
from ingestion.market_adapters import (
    NSE_CM_LEGACY,
    NSE_CM_UDIFF,
    AdapterError,
    Provider,
    ingest_market_file,
)
from ingestion.source_registry import sync_sources
from universe.entities import EntityError, resolve
from universe.equity_list import load_equity_list

RELIANCE = "INE002A01018"
TCS = "INE467B01029"
RETRIEVED = "2024-03-15T19:00:00+05:30"

LEGACY_HEADER = ["SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE", "TOTTRDQTY",
                 "TOTTRDVAL", "TIMESTAMP", "TOTALTRADES", "ISIN", ""]
UDIFF_HEADER = ["TradDt", "BizDt", "Sgmt", "Src", "FinInstrmTp", "FinInstrmId", "ISIN", "TckrSymb", "SctySrs",
                "XpryDt", "FininstrmActlXpryDt", "StrkPric", "OptnTp", "FinInstrmNm", "OpnPric", "HghPric",
                "LwPric", "ClsPric", "LastPric", "PrvsClsgPric", "UndrlygPric", "SttlmPric", "OpnIntrst",
                "ChngInOpnIntrst", "TtlTradgVol", "TtlTrfVal", "TtlNbOfTxsExctd", "SsnId", "NewBrdLotQty",
                "Rmks", "Rsvd1", "Rsvd2", "Rsvd3", "Rsvd4"]

# The same trading day, as (symbol, series, isin, date, open, high, low, close, volume).
DAY = [
    ("RELIANCE", "EQ", RELIANCE, "2024-03-14", "2900.00", "2950.50", "2890.00", "2940.25", "1000000"),
    ("TCS", "EQ", TCS, "2024-03-14", "4000.00", "4050.00", "3990.00", "4020.00", "500000"),
    ("RELIANCE", "BE", RELIANCE, "2024-03-14", "2901.00", "2901.00", "2901.00", "2901.00", "10"),  # not EQ
]
MONTHS = {"03": "MAR"}


def to_csv(header, rows):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def legacy_text(day=DAY):
    rows = []
    for sym, series, isin, d, o, h, l, c, v in day:
        y, m, dd = d.split("-")
        rows.append([sym, series, o, h, l, c, c, o, v, "0", f"{dd}-{MONTHS.get(m, m)}-{y}", "1", isin, ""])
    return to_csv(LEGACY_HEADER, rows)


def udiff_text(day=DAY):
    rows = []
    for sym, series, isin, d, o, h, l, c, v in day:
        values = {"TradDt": d, "BizDt": d, "Sgmt": "CM", "Src": "NSE", "FinInstrmTp": "STK", "ISIN": isin,
                  "TckrSymb": sym, "SctySrs": series, "FinInstrmNm": sym, "OpnPric": o, "HghPric": h,
                  "LwPric": l, "ClsPric": c, "LastPric": c, "PrvsClsgPric": o, "SttlmPric": c,
                  "TtlTradgVol": v, "TtlTrfVal": "0", "TtlNbOfTxsExctd": "1", "SsnId": "F1", "NewBrdLotQty": "1"}
        rows.append([values.get(col, "") for col in UDIFF_HEADER])
    return to_csv(UDIFF_HEADER, rows)


EQUITY_LIST = (
    "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n"
    f"RELIANCE,Reliance Industries Limited,EQ,29-NOV-1995,10,1,{RELIANCE},10\n"
    f"TCS,Tata Consultancy Services Limited,EQ,25-AUG-2004,1,1,{TCS},1\n"
    "BADISIN,Bad Isin Limited,EQ,01-JAN-2010,1,1,INE002A01019,1\n"
    "BADDATE,Bad Date Limited,EQ,2010-01-01,1,1,INE009A01021,1\n"
)


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def count(c, table):
    return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


@pytest.fixture
def conn(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    load_equity_list(c, write(tmp_path, "EQUITY_L.csv", EQUITY_LIST), RETRIEVED, raw_dir=tmp_path / "raw")
    yield c
    c.close()


def trusted(c):
    return c.execute("SELECT isin, trade_date, open_price, high_price, low_price, close_price, volume"
                     " FROM trusted_prices ORDER BY isin").fetchall()


# ---- 40A item 7: provider swap with no downstream change ----

def test_both_nse_formats_give_identical_trusted_prices(tmp_path):
    results = []
    for name, text in (("cm14MAR2024bhav.csv", legacy_text()),
                       ("BhavCopy_NSE_CM_0_0_0_20240314_F_0000.csv", udiff_text())):
        c = connect(":memory:")
        migrate(c)
        sync_sources(c)
        load_equity_list(c, write(tmp_path, f"list_{name}", EQUITY_LIST), RETRIEVED, raw_dir=tmp_path / "raw")
        report = ingest_market_file(c, write(tmp_path, name, text), RETRIEVED, raw_dir=tmp_path / "raw")
        assert (report["rows_trusted"], report["rows_out_of_scope"], report["rows_quarantined"]) == (2, 1, 0)
        results.append((report["provider"], trusted(c)))
        c.close()
    (p1, legacy), (p2, udiff) = results
    assert (p1, p2) == ("nse_cm_bhavcopy_legacy", "nse_cm_bhavcopy_udiff")
    assert legacy == udiff and len(legacy) == 2


def test_a_new_provider_needs_no_downstream_change(conn, tmp_path):
    vendor = Provider(
        name="example_vendor", version="1", source_id="nse_bhavcopy_equity",
        required_columns=("Ticker", "Isin", "Date", "O", "H", "L", "C", "Vol", "Board"),
        scope_column="Board", scope_values=frozenset({"MAIN"}),
        mapping={"symbol": "Ticker", "isin": "Isin", "trade_date": "Date", "open": "O", "high": "H",
                 "low": "L", "close": "C", "volume": "Vol"},
        date_format="%d/%m/%Y",
    )
    text = to_csv(["Ticker", "Isin", "Date", "O", "H", "L", "C", "Vol", "Board"],
                  [["TCS", TCS, "14/03/2024", "4000.00", "4050.00", "3990.00", "4020.00", "500000", "MAIN"]])
    report = ingest_market_file(conn, write(tmp_path, "vendor.csv", text), RETRIEVED,
                                raw_dir=tmp_path / "raw", providers=(vendor,))
    assert report["rows_trusted"] == 1 and report["provider"] == "example_vendor"


def test_provider_details_live_only_in_the_adapter_module():
    # Static check: no other module knows a provider's column names.
    home = PROJECT_ROOT / "src" / "ingestion" / "market_adapters.py"
    pattern = re.compile(r"TckrSymb|TOTTRDQTY|ClsPric|SctySrs|TtlTradgVol")
    offenders = [str(p) for p in (PROJECT_ROOT / "src").rglob("*.py")
                 if p != home and pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


def test_each_run_records_its_provider(conn, tmp_path):
    report = ingest_market_file(conn, write(tmp_path, "u.csv", udiff_text()), RETRIEVED, raw_dir=tmp_path / "raw")
    row = conn.execute("SELECT provider, rows_in_file, rows_out_of_scope, scope_rule FROM adapter_runs"
                       " WHERE run_id = ?", [report["run_id"]]).fetchone()
    assert row == ("nse_cm_bhavcopy_udiff", 3, 1, "SctySrs in ['EQ'] and ISIN not starting with ['INF']")


def test_etfs_and_fund_units_are_out_of_scope_not_quarantined(conn, tmp_path):
    # ADR-003: found on the first real NSE file - 349 ETFs trade in the EQ series.
    etf = ("GOLDBEES", "EQ", "INF204KB17I5", "2024-03-14", "60.00", "61.00", "59.50", "60.50", "100000")
    for text, name in ((udiff_text(DAY + [etf]), "u.csv"), (legacy_text(DAY + [etf]), "l.csv")):
        c = connect(":memory:")
        migrate(c)
        sync_sources(c)
        load_equity_list(c, write(tmp_path, f"list_{name}", EQUITY_LIST), RETRIEVED, raw_dir=tmp_path / "raw")
        report = ingest_market_file(c, write(tmp_path, name, text), RETRIEVED, raw_dir=tmp_path / "raw")
        assert (report["rows_trusted"], report["rows_out_of_scope"], report["rows_quarantined"]) == (2, 2, 0)
        c.close()


# ---- 40G.2: formats change loudly ----

def test_unrecognised_format_fails_loudly_and_stores_nothing(conn, tmp_path):
    path = write(tmp_path, "mystery.csv", "Date,Name,Price\n2024-03-14,TCS,4020\n")
    with pytest.raises(AdapterError, match="Unrecognised file format"):
        ingest_market_file(conn, path, RETRIEVED, raw_dir=tmp_path / "raw")
    assert count(conn, "ingestion_runs") == 0


def test_a_missing_column_is_a_format_change_not_a_partial_read(conn, tmp_path):
    header = [h for h in UDIFF_HEADER if h != "TtlTradgVol"]
    path = write(tmp_path, "changed.csv", to_csv(header, [["2024-03-14"] + [""] * (len(header) - 1)]))
    with pytest.raises(AdapterError):
        ingest_market_file(conn, path, RETRIEVED, raw_dir=tmp_path / "raw")


# ---- translate, never repair ----

def test_out_of_scope_rows_are_counted_not_quarantined(conn, tmp_path):
    report = ingest_market_file(conn, write(tmp_path, "l.csv", legacy_text()), RETRIEVED, raw_dir=tmp_path / "raw")
    assert report["rows_out_of_scope"] == 1 and count(conn, "quarantine") == 0


def test_untranslatable_date_is_quarantined_as_received(conn, tmp_path):
    text = legacy_text().replace("14-MAR-2024", "14/03/2024", 1)
    report = ingest_market_file(conn, write(tmp_path, "l.csv", text), RETRIEVED, raw_dir=tmp_path / "raw")
    assert report["quarantined_by_stage"] == {"schema_and_type": 1}
    raw = json.loads(conn.execute("SELECT raw_record FROM quarantine").fetchone()[0])
    assert raw["TIMESTAMP"] == "14/03/2024" and raw["SYMBOL"] == "RELIANCE"  # the NSE row, as received


def test_provenance_points_at_the_line_in_the_original_file(conn, tmp_path):
    ingest_market_file(conn, write(tmp_path, "u.csv", udiff_text()), RETRIEVED, raw_dir=tmp_path / "raw")
    line = conn.execute("SELECT p.row_number FROM price_provenance p JOIN trusted_prices t"
                        " ON t.price_id = p.price_id WHERE t.isin = ?", [TCS]).fetchone()[0]
    assert line == 3  # header is line 1, RELIANCE line 2, TCS line 3


def test_old_or_unknown_symbol_fails_closed(conn, tmp_path):
    day = [("RELIANCEOLD", "EQ", RELIANCE, "2024-03-14", "2900.00", "2950.50", "2890.00", "2940.25", "1000")]
    report = ingest_market_file(conn, write(tmp_path, "u.csv", udiff_text(day)), RETRIEVED, raw_dir=tmp_path / "raw")
    assert report["quarantined_by_stage"] == {"entity_resolution": 1}


# ---- file handling ----

def test_zip_files_are_read_and_the_zip_itself_is_the_raw_artifact(conn, tmp_path):
    zipped = tmp_path / "BhavCopy_NSE_CM_0_0_0_20240314_F_0000.csv.zip"
    with zipfile.ZipFile(zipped, "w") as z:
        z.writestr("BhavCopy_NSE_CM_0_0_0_20240314_F_0000.csv", udiff_text())
    report = ingest_market_file(conn, zipped, RETRIEVED, raw_dir=tmp_path / "raw")
    assert report["rows_trusted"] == 2
    assert report["sha256"] == hashlib.sha256(zipped.read_bytes()).hexdigest()


def test_zip_with_more_than_one_csv_is_refused(conn, tmp_path):
    zipped = tmp_path / "two.zip"
    with zipfile.ZipFile(zipped, "w") as z:
        z.writestr("a.csv", udiff_text())
        z.writestr("b.csv", udiff_text())
    with pytest.raises(AdapterError, match="exactly one"):
        ingest_market_file(conn, zipped, RETRIEVED, raw_dir=tmp_path / "raw")


def test_file_with_nothing_in_scope_is_refused(conn, tmp_path):
    path = write(tmp_path, "be_only.csv", legacy_text([DAY[2]]))
    with pytest.raises(NoDataError):
        ingest_market_file(conn, path, RETRIEVED, raw_dir=tmp_path / "raw")
    assert count(conn, "ingestion_runs") == 0


def test_empty_file_is_refused(conn, tmp_path):
    with pytest.raises(NoDataError):
        ingest_market_file(conn, write(tmp_path, "empty.csv", ""), RETRIEVED, raw_dir=tmp_path / "raw")


# ---- the equity list (a current snapshot) ----

def test_equity_list_adds_companies_and_records_rejections(conn):
    assert count(conn, "entities") == 2
    assert resolve(conn, "TCS", "2010-01-01", alias_type="nse_symbol") == TCS
    with pytest.raises(EntityError):
        resolve(conn, "TCS", "2004-08-24", alias_type="nse_symbol")  # before listing
    load = conn.execute("SELECT entities_added, already_present, rejected FROM entity_list_loads").fetchone()
    assert load == (2, 0, 2)
    reasons = [r[0] for r in conn.execute("SELECT reason FROM entity_list_rejections ORDER BY row_number")]
    assert "check digit" in reasons[0] and "DD-MON-YYYY" in reasons[1]
    events = conn.execute("SELECT COUNT(*) FROM entity_events WHERE event_type = 'listing'").fetchone()[0]
    assert events == 2


def test_reloading_the_list_changes_nothing(conn, tmp_path):
    report = load_equity_list(conn, write(tmp_path, "EQUITY_L_2.csv", EQUITY_LIST + "\n"), RETRIEVED,
                              raw_dir=tmp_path / "raw")
    assert (report["entities_added"], report["already_present"], report["rejected"]) == (0, 2, 2)
    assert count(conn, "entities") == 2 and count(conn, "entity_aliases") == 2


@pytest.mark.parametrize("line, reason", [
    (f"RELIANCE,Reliance Industries Ltd,EQ,29-NOV-1995,10,1,{RELIANCE},10", "name differs"),
    (f"RELIANCENEW,Reliance Industries Limited,EQ,29-NOV-1995,10,1,{RELIANCE},10", "symbol differs"),
    ("TCS,Some Other Company Limited,EQ,01-JAN-2020,1,1,INE009A01021,1", "already belongs to"),
])
def test_a_snapshot_never_overwrites_or_guesses(conn, tmp_path, line, reason):
    header = EQUITY_LIST.splitlines()[0]
    report = load_equity_list(conn, write(tmp_path, "changed.csv", f"{header}\n{line}\n"), RETRIEVED,
                              raw_dir=tmp_path / "raw")
    assert report["rejected"] == 1 and reason in report["first_rejections"][0][1]
    assert count(conn, "entities") == 2
    names = {r[0] for r in conn.execute("SELECT legal_name FROM entities")}
    assert "Reliance Industries Limited" in names


def test_a_rejected_row_leaves_nothing_half_written(conn, tmp_path, monkeypatch):
    def failing_alias(*args, **kwargs):
        raise EntityError("simulated failure after the entity was added")
    monkeypatch.setattr(equity_list, "add_alias", failing_alias)
    header = EQUITY_LIST.splitlines()[0]
    report = load_equity_list(conn, write(tmp_path, "new.csv", f"{header}\nINFY,Infosys Limited,EQ,08-FEB-1995,5,1,INE009A01021,5\n"),
                              RETRIEVED, raw_dir=tmp_path / "raw")
    assert report["rejected"] == 1
    assert conn.execute("SELECT COUNT(*) FROM entities WHERE isin = 'INE009A01021'").fetchone()[0] == 0


def test_equity_list_with_wrong_columns_is_refused(conn, tmp_path):
    with pytest.raises(AdapterError, match="missing columns"):
        load_equity_list(conn, write(tmp_path, "x.csv", "A,B\n1,2\n"), RETRIEVED, raw_dir=tmp_path / "raw")


# ---- migration and acceptance record ----

def test_adapter_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 6)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not {"adapter_runs", "entity_list_loads", "entity_list_rejections"} & names
    assert "universes" in names
    c.close()


def test_providers_are_frozen_definitions():
    with pytest.raises(dataclasses.FrozenInstanceError):
        NSE_CM_UDIFF.scope_column = "anything"
    assert NSE_CM_LEGACY.source_id == NSE_CM_UDIFF.source_id == "nse_bhavcopy_equity"


def test_stage_7a_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_07A_acceptance.yaml"]
    # PROTOTYPE until real NSE files have gone through end to end; then ACCEPTED (40C).
    assert record["status"] in {"PROTOTYPE", "ACCEPTED_MARKET_DATA_ADAPTER_BASELINE"}
    assert record["not_claimed"]["corporate-action adjustment (Stage 7B)"] is False
