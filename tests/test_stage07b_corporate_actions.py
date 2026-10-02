"""Stage 7B acceptance tests: corporate-action adjustment.

40A item 13 / 40B step 6: a known split produces a continuous adjusted series
and a discontinuous raw series.
6C: raw prices are immutable; the adjusted series carries its own identity;
only splits and simple bonuses produce factors, from verified ratios; dividends
and buybacks need none; everything else is blocked.
6C.1: a blocked action fails closed for that security's window only.
Criterion 64: no factor is ever inferred from an observed price jump.
"""
import sqlite3

import pytest

from core.config import PROJECT_ROOT
from core.database import connect, migrate, rollback
from data_quality.trust_chain import ingest_price_file
from features.price_series import AdjustmentBlocked, SeriesError, adjusted_series, raw_series
from ingestion.corporate_actions import POLICY, POLICY_VERSION, CorporateActionError, record_action
from ingestion.source_registry import sync_sources
from provenance.raw_store import store_raw_artifact
from universe.entities import add_alias, add_entity

SPLITCO = "INE002A01018"
BONUSCO = "INE467B01029"
OTHERCO = "INE009A01021"
WINDOW = ("2026-09-01", "2026-09-04")

# (symbol, isin, date, open, high, low, close, volume)
PRICES = [
    ("SPLITCO", SPLITCO, "2026-09-01", "990.00", "1005.00", "985.00", "1000.00", "100000"),
    ("SPLITCO", SPLITCO, "2026-09-02", "1000.00", "1015.00", "995.00", "1010.00", "100000"),
    ("SPLITCO", SPLITCO, "2026-09-03", "202.00", "205.00", "201.00", "204.00", "500000"),  # ex-date of a 1:5 split
    ("SPLITCO", SPLITCO, "2026-09-04", "204.00", "207.00", "203.00", "206.00", "500000"),
    ("BONUSCO", BONUSCO, "2026-09-01", "400.00", "402.00", "398.00", "400.00", "1000"),
    ("BONUSCO", BONUSCO, "2026-09-02", "400.00", "404.00", "399.00", "402.00", "1000"),
    ("BONUSCO", BONUSCO, "2026-09-03", "201.00", "203.00", "200.00", "202.00", "2000"),  # ex-date of a 1:1 bonus
    ("BONUSCO", BONUSCO, "2026-09-04", "202.00", "204.00", "201.00", "203.00", "2000"),
    ("OTHERCO", OTHERCO, "2026-09-01", "100.00", "101.00", "99.00", "100.00", "500"),
    ("OTHERCO", OTHERCO, "2026-09-02", "100.00", "101.00", "99.00", "100.50", "500"),
    ("OTHERCO", OTHERCO, "2026-09-03", "50.00", "51.00", "49.00", "50.00", "500"),        # halves with NO action recorded
    ("OTHERCO", OTHERCO, "2026-09-04", "50.00", "51.00", "49.00", "50.50", "500"),
]


@pytest.fixture
def conn(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    for isin, symbol in ((SPLITCO, "SPLITCO"), (BONUSCO, "BONUSCO"), (OTHERCO, "OTHERCO")):
        add_entity(c, isin, f"{symbol} Limited")
        add_alias(c, isin, "nse_symbol", symbol, "2000-01-01")
    lines = ["symbol,isin,trade_date,open,high,low,close,volume"] + [",".join(p) for p in PRICES]
    path = tmp_path / "prices.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = ingest_price_file(c, "nse_bhavcopy_equity", path, "2026-09-05T19:00:00+05:30", raw_dir=tmp_path / "raw")
    assert report["rows_trusted"] == len(PRICES)
    yield c
    c.close()


@pytest.fixture
def evidence_file(conn, tmp_path):
    path = tmp_path / "nse_corporate_actions.csv"
    path.write_text("SYMBOL,PURPOSE,EX-DATE\nSPLITCO,Face Value Split From Rs 10 To Rs 2,03-Sep-2026\n", encoding="utf-8")
    artifact_id, _ = store_raw_artifact(conn, "nse_corporate_actions", path, "2026-09-05T19:00:00+05:30",
                                        raw_dir=tmp_path / "raw")
    return artifact_id


def record(conn, artifact_id, isin, action_type, ex_date="2026-09-03", before=None, after=None):
    return record_action(conn, isin, action_type, ex_date, f"{action_type} terms as published",
                         artifact_id, "NSE corporate actions file", before, after)


def daily_moves(closes):
    return [b / a - 1 for a, b in zip(closes, closes[1:])]


# ---- 40A item 13: the acceptance test ----

def test_a_known_split_gives_continuous_adjusted_and_discontinuous_raw(conn, evidence_file):
    action_id = record(conn, evidence_file, SPLITCO, "split", before=1, after=5)
    before = conn.execute("SELECT * FROM trusted_prices ORDER BY price_id").fetchall()

    raw = raw_series(conn, SPLITCO, *WINDOW)
    adjusted = adjusted_series(conn, SPLITCO, *WINDOW)

    assert min(daily_moves(raw.closes())) < -0.75                         # raw: an 80% "crash" that never happened
    assert all(abs(m) < 0.02 for m in daily_moves(adjusted.closes()))     # adjusted: continuous
    assert adjusted.closes() == pytest.approx([200.0, 202.0, 204.0, 206.0])
    assert [r[5] for r in adjusted.rows] == pytest.approx([500000, 500000, 500000, 500000])
    # The adjusted series carries its own identity.
    assert (adjusted.basis, adjusted.policy_version, adjusted.actions_applied) == ("adjusted", POLICY_VERSION, (action_id,))
    assert (raw.basis, raw.actions_applied) == ("raw", ())
    # Negative assertion: raw prices are untouched.
    assert conn.execute("SELECT * FROM trusted_prices ORDER BY price_id").fetchall() == before


def test_a_simple_bonus_is_back_adjusted(conn, evidence_file):
    record(conn, evidence_file, BONUSCO, "bonus", before=1, after=2)  # 1 bonus share for every 1 held
    adjusted = adjusted_series(conn, BONUSCO, *WINDOW)
    assert adjusted.closes() == pytest.approx([200.0, 201.0, 202.0, 203.0])


def test_a_reverse_split_is_back_adjusted_upwards(conn, evidence_file):
    record(conn, evidence_file, OTHERCO, "split", before=2, after=1)  # 2 shares become 1
    adjusted = adjusted_series(conn, OTHERCO, "2026-09-01", "2026-09-02")
    assert adjusted.closes() == raw_series(conn, OTHERCO, "2026-09-01", "2026-09-02").closes()  # ex-date outside window
    adjusted = adjusted_series(conn, OTHERCO, *WINDOW)
    assert adjusted.closes()[:2] == pytest.approx([200.0, 201.0])


@pytest.mark.parametrize("action_type", ["dividend", "buyback"])
def test_dividends_and_buybacks_need_no_adjustment(conn, evidence_file, action_type):
    record(conn, evidence_file, SPLITCO, action_type)
    assert adjusted_series(conn, SPLITCO, *WINDOW).closes() == raw_series(conn, SPLITCO, *WINDOW).closes()


# ---- criterion 64: never infer a factor from prices ----

def test_a_price_jump_without_a_recorded_action_is_never_adjusted(conn):
    raw = raw_series(conn, OTHERCO, *WINDOW)
    adjusted = adjusted_series(conn, OTHERCO, *WINDOW)
    assert min(daily_moves(raw.closes())) < -0.45          # the price halved...
    assert adjusted.closes() == raw.closes()               # ...and nothing was invented to explain it
    assert adjusted.actions_applied == ()


def test_the_factor_source_never_reads_prices():
    # Static check: the module that defines factors cannot see prices at all.
    text = (PROJECT_ROOT / "src" / "ingestion" / "corporate_actions.py").read_text(encoding="utf-8")
    assert "trusted_prices" not in text and "close_price" not in text


# ---- 6C.1: blocked actions fail closed, for that security's window only ----

@pytest.mark.parametrize("action_type", ["rights", "special_dividend", "merger", "demerger", "complex_bonus", "unknown"])
def test_unsupported_actions_block_the_window(conn, evidence_file, action_type):
    record(conn, evidence_file, SPLITCO, action_type)
    with pytest.raises(AdjustmentBlocked, match="fails closed"):
        adjusted_series(conn, SPLITCO, *WINDOW)


def test_blocking_is_limited_to_the_security_and_window(conn, evidence_file):
    record(conn, evidence_file, SPLITCO, "rights")
    assert len(adjusted_series(conn, BONUSCO, *WINDOW).rows) == 4               # other security: fine
    assert len(adjusted_series(conn, SPLITCO, "2026-09-01", "2026-09-02").rows) == 2  # window before ex-date
    assert len(adjusted_series(conn, SPLITCO, "2026-09-03", "2026-09-04").rows) == 2  # window starts on ex-date
    assert len(raw_series(conn, SPLITCO, *WINDOW).rows) == 4                    # raw is always available


# ---- recording rules ----

@pytest.mark.parametrize("before, after", [(None, 5), (1, None), (0, 5), (-1, 5), (5, 5), (1.0, 5), (True, 5)])
def test_a_factor_needs_a_valid_whole_number_ratio(conn, evidence_file, before, after):
    with pytest.raises(CorporateActionError):
        record(conn, evidence_file, SPLITCO, "split", before=before, after=after)


def test_a_bonus_can_only_increase_shares(conn, evidence_file):
    with pytest.raises(CorporateActionError, match="increase"):
        record(conn, evidence_file, BONUSCO, "bonus", before=2, after=1)


@pytest.mark.parametrize("action_type", ["dividend", "buyback", "rights", "merger", "unknown"])
def test_non_factor_actions_cannot_carry_a_ratio(conn, evidence_file, action_type):
    with pytest.raises(CorporateActionError, match="must not carry a share ratio"):
        record(conn, evidence_file, SPLITCO, action_type, before=1, after=2)


@pytest.mark.parametrize("kwargs", [
    {"action_type": "stock_split"},          # not in the policy
    {"ex_date": "03-09-2026"},               # bad date
    {"terms_text": " "},                     # source wording missing
    {"evidence": ""},                        # no evidence
    {"isin": "INE040A01034"},                # unknown company
])
def test_incomplete_actions_are_refused(conn, evidence_file, kwargs):
    args = {"isin": SPLITCO, "action_type": "split", "ex_date": "2026-09-03", "terms_text": "1:5 split",
            "artifact_id": evidence_file, "evidence": "NSE file", "shares_before": 1, "shares_after": 5}
    args.update(kwargs)
    with pytest.raises(CorporateActionError):
        record_action(conn, **args)
    assert conn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0] == 0


def test_an_action_without_a_source_file_is_refused(conn):
    with pytest.raises(CorporateActionError, match="source file"):
        record_action(conn, SPLITCO, "split", "2026-09-03", "1:5", 999, "x", 1, 5)


def test_actions_are_never_overwritten(conn, evidence_file):
    record(conn, evidence_file, SPLITCO, "split", before=1, after=5)
    with pytest.raises(CorporateActionError, match="never overwritten"):
        record(conn, evidence_file, SPLITCO, "split", before=1, after=10)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE corporate_actions SET shares_after = 10")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM corporate_actions")


def test_bad_windows_are_refused(conn):
    with pytest.raises(SeriesError):
        adjusted_series(conn, SPLITCO, "2026-09-04", "2026-09-01")
    with pytest.raises(SeriesError):
        raw_series(conn, SPLITCO, "20260901", "2026-09-04")


# ---- the policy states intent and implementation (6C) ----

def test_policy_matches_the_architecture_table():
    treatments = {k: v[1] for k, v in POLICY.items()}
    assert treatments == {
        "split": "factor", "bonus": "factor",
        "dividend": "no_adjustment", "buyback": "no_adjustment",
        "rights": "blocked", "special_dividend": "blocked", "merger": "blocked",
        "demerger": "blocked", "complex_bonus": "blocked", "unknown": "blocked",
    }
    assert all(intent.strip() for intent, _ in POLICY.values())


# ---- migration and acceptance record ----

def test_corporate_action_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 7)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert "corporate_actions" not in names and "adapter_runs" in names
    c.close()


def test_stage_7b_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record_ = load_acceptance_records()["STAGE_07B_acceptance.yaml"]
    assert record_["status"] in {"PROTOTYPE", "ACCEPTED_CORPORATE_ACTION_ADJUSTMENT_BASELINE"}
    assert record_["negative_assertions"]["factor inferred from a price jump"] is False
