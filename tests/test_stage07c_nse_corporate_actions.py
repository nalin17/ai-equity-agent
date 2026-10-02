"""Stage 7C tests: reading NSE's corporate actions file (architecture 6C.2).

Only mechanically complete wordings produce factors; everything else fails
closed. Rows attach to companies by symbol as of the ex-date, with a name
cross-check. Same-day rows are combined. Recorded actions are never
overwritten; contradictions are recorded and a contradicted factor blocks.
The wordings below are taken from NSE's real file of 2026-10-02.
"""
import pytest

from core.config import PROJECT_ROOT
from core.database import connect, migrate, rollback
from data_quality.trust_chain import NoDataError, ingest_price_file
from features.price_series import AdjustmentBlocked, adjusted_series
from ingestion.market_adapters import AdapterError
from ingestion.nse_corporate_actions import classify_purpose, load_corporate_actions, normalise_name
from ingestion.source_registry import sync_sources
from universe.entities import add_alias, add_entity, validate_isin

RETRIEVED = "2026-10-02T15:21:00+05:30"
HEADER = '"SYMBOL","COMPANY NAME","SERIES","PURPOSE","FACE VALUE","EX-DATE","RECORD DATE",' \
         '"BOOK CLOSURE START DATE","BOOK CLOSURE END DATE"'


def make_isin(base):
    for digit in "0123456789":
        try:
            return validate_isin(base + digit)
        except Exception:
            continue


COMPANIES = {  # symbol -> (isin, registry name)
    "SPLITCO": (make_isin("INE100A0101"), "Split Company Limited"),
    "BONUSCO": (make_isin("INE101A0101"), "Bonus Company Ltd"),
    "DIVCO": (make_isin("INE102A0101"), "Dividend Co. Limited"),
    "MIXCO": (make_isin("INE103A0101"), "Mixed Actions Limited"),
    "TYPOCO": (make_isin("INE104A0101"), "Typo Company Limited"),
}


def row(symbol, name, purpose, fv="10", ex="22-Sep-2026", series="EQ"):
    return f'"{symbol}","{name}","{series}","{purpose}","{fv}","{ex}","{ex}","-","-"'


@pytest.fixture
def conn():
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    for symbol, (isin, name) in COMPANIES.items():
        add_entity(c, isin, name)
        add_alias(c, isin, "nse_symbol", symbol, "2000-01-01")
    yield c
    c.close()


def load(c, tmp_path, lines, name="CF-CA-equities.csv"):
    path = tmp_path / name
    path.write_text("\ufeff" + "\n".join([HEADER] + lines), encoding="utf-8")
    return load_corporate_actions(c, path, RETRIEVED, raw_dir=tmp_path / "raw")


def actions(c, symbol):
    isin = COMPANIES[symbol][0]
    return c.execute("SELECT action_type, treatment, shares_before, shares_after, terms_text FROM corporate_actions"
                     " WHERE isin = ? ORDER BY action_type", [isin]).fetchall()


# ---- classifying NSE's real wordings ----

@pytest.mark.parametrize("purpose, fv, expected", [
    ("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", "2", ("split", 1, 5)),
    ("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", "10", ("split", 1, 5)),
    ("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share", "1", ("split", 1, 10)),
    ("Face Value Split (Sub-Division) - From Rs 5/- Per Share To Rs 2/- Per Share", "2", ("split", 2, 5)),
    ("Bonus 1:3", "2", ("bonus", 3, 4)),          # 1 new share for every 3 held
    ("Bonus 2:1", "2", ("bonus", 1, 3)),          # 2 new shares for every 1 held
    ("Bonus 1:1", "5", ("bonus", 1, 2)),
    ("Dividend - Rs 5 Per Share", "1", ("dividend", None, None)),
    ("Dividend - Re 0.05 Per Share", "1", ("dividend", None, None)),
    ("Dividend - Rs. 3 Per Share", "1", ("dividend", None, None)),
    ("Dividend - Rs3 Per Share", "1", ("dividend", None, None)),
    ("Dividend - Re  0.50 Per Share", "1", ("dividend", None, None)),
    ("Dividend - Rs 2 Per Sh", "1", ("dividend", None, None)),
    ("Interim Dividend - Rs 1.50 Per Share", "1", ("dividend", None, None)),
    ("Buy Back", "1", ("buyback", None, None)),
    ("Special Dividend - Rs 2 Per Share", "1", ("special_dividend", None, None)),
    ("Dividend - Rs 5 Per Share/Special Dividend - Rs 2 Per Share", "1", ("special_dividend", None, None)),
    ("Dividend - Rs 5 Per Share & Special Dividend Re 0.50 Per Share", "1", ("special_dividend", None, None)),
    ("Rights 3:2 @ Premium Re. 0.63/-", "1", ("rights", None, None)),
    ("Rights - 7 Ccps And 7 Warrants:40", "1", ("rights", None, None)),
    ("Demerger", "2", ("demerger", None, None)),
    ("Scheme Of Arrangement - Bonus Ncrps 46:1", "5", ("complex_bonus", None, None)),
    ("Scheme Of Amalgamation", "2", ("merger", None, None)),
    ("Intdividend - Rs 160 Per Share", "10", ("unknown", None, None)),     # NSE typo: never guessed
    ("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", "5", ("unknown", None, None)),
    ("Face Value Split (Sub-Division) - From Rs 2/- Per Share To Rs 10/- Per Share", "2", ("unknown", None, None)),
    ("Annual General Meeting", "10", ("unknown", None, None)),
])
def test_wordings_are_classified_mechanically(purpose, fv, expected):
    assert classify_purpose(purpose, fv)[:3] == expected


def test_names_are_compared_after_normalising():
    assert normalise_name("Dividend Co. Limited") == normalise_name("DIVIDEND CO LTD")
    assert normalise_name("Split Company Limited") != normalise_name("Split Holdings Limited")


# ---- loading a file ----

def test_a_real_style_file_is_loaded(conn, tmp_path):
    report = load(conn, tmp_path, [
        row("SPLITCO", "Split Company Limited",
            "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", fv="2"),
        row("BONUSCO", "BONUS COMPANY LIMITED", "Bonus 1:3", fv="2", ex="10-Jul-2026"),
        row("DIVCO", "Dividend Co Ltd", "Dividend - Rs 5 Per Share", fv="1"),
        row("REITCO", "Some Trust", "Distribution - Rs 2 Per Unit", series="RR"),
        row("GOVT", "Bond", "Interest Payment", series="GS"),
    ])
    assert (report["rows_in_file"], report["rows_out_of_scope"], report["actions_recorded"],
            report["rejected"], report["conflicts"]) == (5, 2, 3, 0, 0)
    assert actions(conn, "SPLITCO")[0][:4] == ("split", "factor", 1, 5)
    assert actions(conn, "BONUSCO")[0][:4] == ("bonus", "factor", 3, 4)
    assert actions(conn, "DIVCO")[0][:2] == ("dividend", "no_adjustment")


def test_same_day_rows_are_combined_not_lost(conn, tmp_path):
    load(conn, tmp_path, [
        row("MIXCO", "Mixed Actions Limited", "Special Dividend - Rs 2 Per Share", fv="1", ex="10-Jul-2026"),
        row("MIXCO", "Mixed Actions Limited", "Dividend - Rs 5 Per Share", fv="1", ex="10-Jul-2026"),
        row("DIVCO", "Dividend Co Limited", "Interim Dividend - Re 0.80 Per Share", fv="1", ex="21-Aug-2026"),
        row("DIVCO", "Dividend Co Limited", "Interim Dividend - Rs 1.50 Per Share", fv="1", ex="21-Aug-2026"),
    ])
    assert [a[0] for a in actions(conn, "MIXCO")] == ["dividend", "special_dividend"]
    (div,) = actions(conn, "DIVCO")
    assert div[4] == "Interim Dividend - Re 0.80 Per Share | Interim Dividend - Rs 1.50 Per Share"


def test_contradictory_ratios_on_the_same_day_become_unknown(conn, tmp_path):
    load(conn, tmp_path, [
        row("SPLITCO", "Split Company Limited",
            "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", fv="2"),
        row("SPLITCO", "Split Company Limited",
            "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 5/- Per Share", fv="5"),
    ])
    assert [a[:2] for a in actions(conn, "SPLITCO")] == [("unknown", "blocked")]


@pytest.mark.parametrize("line, reason", [
    (row("NOSUCH", "No Such Limited", "Dividend - Rs 5 Per Share"), "not attached"),
    (row("SPLITCO", "Totally Different Limited", "Dividend - Rs 5 Per Share"), "name differs"),
    (row("SPLITCO", "Split Company Limited", "Dividend - Rs 5 Per Share", ex="2026-09-22"), "EX-DATE"),
])
def test_rows_that_cannot_be_attached_are_rejected_and_recorded(conn, tmp_path, line, reason):
    report = load(conn, tmp_path, [line])
    assert report["rejected"] == 1 and reason in report["first_problems"][0][1]
    assert conn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0] == 0
    assert conn.execute("SELECT kind FROM ca_file_rejections").fetchone()[0] == "rejected"


def test_symbols_are_matched_as_of_the_ex_date(conn, tmp_path):
    # NEWCO only started trading under this symbol on 2026-10-01.
    isin = make_isin("INE105A0101")
    add_entity(conn, isin, "New Company Limited")
    add_alias(conn, isin, "nse_symbol", "NEWCO", "2026-10-01")
    report = load(conn, tmp_path, [row("NEWCO", "New Company Limited", "Bonus 1:1", ex="22-Sep-2026")])
    assert report["rejected"] == 1 and "not attached" in report["first_problems"][0][1]


def test_a_typo_is_recorded_as_unknown_and_blocks(conn, tmp_path):
    load(conn, tmp_path, [row("TYPOCO", "Typo Company Limited", "Intdividend - Rs 160 Per Share")])
    assert actions(conn, "TYPOCO")[0][:2] == ("unknown", "blocked")


# ---- reloading: never overwrite, record contradictions ----

def test_reloading_the_same_actions_changes_nothing(conn, tmp_path):
    lines = [row("DIVCO", "Dividend Co Limited", "Dividend - Rs 5 Per Share", fv="1")]
    load(conn, tmp_path, lines, "first.csv")
    report = load(conn, tmp_path, lines + [""], "second.csv")  # different bytes, same content
    assert (report["actions_recorded"], report["already_present"], report["conflicts"]) == (0, 1, 0)


def test_a_contradicted_split_is_recorded_as_conflict_and_blocks(conn, tmp_path):
    split = "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs {}/- Per Share"
    load(conn, tmp_path, [row("SPLITCO", "Split Company Limited", split.format(2), fv="2")], "first.csv")
    report = load(conn, tmp_path, [row("SPLITCO", "Split Company Limited", split.format(5), fv="5")], "second.csv")
    assert report["conflicts"] == 1
    kinds = {a[0]: a[1] for a in actions(conn, "SPLITCO")}
    assert kinds == {"split": "factor", "unknown": "blocked"}
    assert actions(conn, "SPLITCO")[0][4] != split.format(5)  # the recorded split was not overwritten


# ---- whole-file problems ----

def test_wrong_file_is_refused(conn, tmp_path):
    path = tmp_path / "x.csv"
    path.write_text("A,B\n1,2\n", encoding="utf-8")
    with pytest.raises(AdapterError, match="missing columns"):
        load_corporate_actions(conn, path, RETRIEVED, raw_dir=tmp_path / "raw")


def test_empty_file_is_refused(conn, tmp_path):
    with pytest.raises(NoDataError):
        load(conn, tmp_path, [])


# ---- end to end: file -> action -> adjusted prices ----

def test_end_to_end_split_from_the_file_adjusts_prices(conn, tmp_path):
    isin = COMPANIES["SPLITCO"][0]
    prices = tmp_path / "prices.csv"
    prices.write_text("symbol,isin,trade_date,open,high,low,close,volume\n"
                      f"SPLITCO,{isin},2026-09-21,1000.00,1010.00,990.00,1000.00,100\n"
                      f"SPLITCO,{isin},2026-09-22,201.00,203.00,199.00,202.00,500\n", encoding="utf-8")
    ingest_price_file(conn, "nse_bhavcopy_equity", prices, RETRIEVED, raw_dir=tmp_path / "raw")
    load(conn, tmp_path, [row("SPLITCO", "Split Company Limited",
                              "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", fv="2")])
    adjusted = adjusted_series(conn, isin, "2026-09-21", "2026-09-22")
    assert adjusted.closes() == pytest.approx([200.0, 202.0])


def test_end_to_end_unknown_wording_blocks_the_window(conn, tmp_path):
    load(conn, tmp_path, [row("TYPOCO", "Typo Company Limited", "Intdividend - Rs 160 Per Share")])
    with pytest.raises(AdjustmentBlocked):
        adjusted_series(conn, COMPANIES["TYPOCO"][0], "2026-09-21", "2026-09-22")


# ---- static check, migration, acceptance record ----

def test_the_reader_never_reads_prices():
    text = (PROJECT_ROOT / "src" / "ingestion" / "nse_corporate_actions.py").read_text(encoding="utf-8")
    assert "trusted_prices" not in text and "close_price" not in text


def test_reader_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 8)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not {"ca_file_loads", "ca_file_rejections"} & names and "corporate_actions" in names
    c.close()


def test_stage_7c_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record_ = load_acceptance_records()["STAGE_07C_acceptance.yaml"]
    assert record_["status"] in {"PROTOTYPE", "ACCEPTED_NSE_CORPORATE_ACTION_READER_BASELINE"}
    assert record_["negative_assertions"]["unrecognised wording guessed"] is False
