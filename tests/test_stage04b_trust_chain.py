"""Stage 4, part 2: the Data Trust chain.

40B step 3 acceptance: a deliberately corrupted input is quarantined, not ingested.
Section 4: ordered stages; each may quarantine, none may repair; the same fact
twice is one fact with two provenance records; conflicts are never averaged.
4C.1: an empty file is never stored as if it were data.
40A item 11: every stored fact resolves to a raw artifact hash.
5B: a trusted price is current-decision eligible from our retrieval time, but
replay eligible only with a proven publication time.
"""
import hashlib
import json
from pathlib import Path

import pytest

import data_quality.trust_chain as trust_chain
from core.database import connect, migrate
from data_quality.trust_chain import (
    NoDataError,
    RecordRejected,
    TrustChainError,
    TrustStage,
    check_schema_and_type,
    ingest_price_file,
)
from ingestion.source_registry import SourceRegistryError, sync_sources
from provenance.availability import Availability, PitClaim, price_availability
from provenance.raw_store import ArtifactError
from universe.entities import add_alias, add_entity

RELIANCE = "INE002A01018"
TCS = "INE467B01029"
INFOSYS = "INE009A01021"  # valid ISIN, deliberately NOT loaded as an entity
SOURCE = "nse_bhavcopy_equity"
RETRIEVED = "2024-03-15T19:00:00+05:30"
HEADER = "symbol,isin,trade_date,open,high,low,close,volume"

CORRUPTED_FILE = "\n".join([
    HEADER,
    f"RELIANCE,{RELIANCE},2024-03-14,2900.00,2950.50,2890.00,2940.25,1000000",  # row 2: good
    f"TCS,{TCS},2024-03-14,4000.00,4050.00,3990.00,4020.00,500000",             # row 3: good
    f"RELIANCE,{RELIANCE},2024-03-12,2900.00,2950.00,2890.00,abc,1000",         # row 4: close not a number
    f"TCS,{TCS},2024-03-12,4000.00,4050.00,3990.00,4020.00,",                   # row 5: volume empty
    f"RELIANCE,{RELIANCE},2024-03-20,2900.00,2950.00,2890.00,2940.00,1000",     # row 6: dated after retrieval
    f"INFY,{INFOSYS},2024-03-14,1600.00,1620.00,1590.00,1610.00,2000",          # row 7: unknown company
    f"TCS,{RELIANCE},2024-03-11,2900.00,2950.00,2890.00,2940.00,1000",          # row 8: symbol/ISIN mismatch
    f"RELIANCE,{RELIANCE},2024-03-13,2900.00,2850.00,2950.00,2900.00,1000",     # row 9: low above high
    f"TCS,{TCS},2024-03-13,4000.00,4050.00,3990.00,4020.00,500000",             # row 10: contradicts row 11
    f"TCS,{TCS},2024-03-13,4000.00,4050.00,3990.00,4025.00,500000",             # row 11: contradicts row 10
    f"RELIANCE,{RELIANCE},2024-03-14,2900.00,2950.50,2890.00,2940.25,1000000",  # row 12: exact repeat of row 2
]) + "\n"


@pytest.fixture
def conn():
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    add_entity(c, RELIANCE, "Reliance Industries Limited")
    add_alias(c, RELIANCE, "nse_symbol", "RELIANCE", "1995-11-29")
    add_entity(c, TCS, "Tata Consultancy Services Limited")
    add_alias(c, TCS, "nse_symbol", "TCS", "2004-08-25")
    yield c
    c.close()


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def count(c, table):
    return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---- 40B step 3 acceptance ----

def test_corrupted_input_is_quarantined_not_ingested(conn, tmp_path):
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    report = ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")

    assert report["rows_total"] == 11
    assert report["rows_trusted"] == 2
    assert report["rows_duplicate"] == 1
    assert report["rows_quarantined"] == 8
    assert report["quarantined_by_stage"] == {
        "schema_and_type": 2,
        "timestamp_and_availability": 1,
        "entity_resolution": 2,
        "anomaly_detection": 1,
        "deduplication": 2,
    }
    trusted = conn.execute("SELECT isin, trade_date FROM trusted_prices ORDER BY isin").fetchall()
    assert trusted == [(RELIANCE, "2024-03-14"), (TCS, "2024-03-14")]
    quarantined_rows = [r[0] for r in conn.execute("SELECT row_number FROM quarantine ORDER BY row_number")]
    assert quarantined_rows == [4, 5, 6, 7, 8, 9, 10, 11]


def test_quarantined_record_is_kept_exactly_as_received_and_never_repaired(conn, tmp_path):
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")
    stage, reason, raw = conn.execute(
        "SELECT failed_stage, reason, raw_record FROM quarantine WHERE row_number = 9").fetchone()
    assert stage == "anomaly_detection"
    assert reason == "low 2950.0 is above high 2850.0"
    assert json.loads(raw)["low"] == "2950.00" and json.loads(raw)["high"] == "2850.00"  # not swapped
    # Negative assertion: no repaired version reached the trusted table.
    assert conn.execute(
        "SELECT COUNT(*) FROM trusted_prices WHERE isin = ? AND trade_date = '2024-03-13'", [RELIANCE]
    ).fetchone()[0] == 0


def test_exact_repeat_is_one_fact_with_two_provenance_records(conn, tmp_path):
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")
    price_id = conn.execute(
        "SELECT price_id FROM trusted_prices WHERE isin = ? AND trade_date = '2024-03-14'", [RELIANCE]
    ).fetchone()[0]
    rows = [r[0] for r in conn.execute(
        "SELECT row_number FROM price_provenance WHERE price_id = ? ORDER BY row_number", [price_id])]
    assert rows == [2, 12]


# ---- cross-source consistency ----

def test_conflict_with_trusted_value_is_quarantined_never_overwritten(conn, tmp_path):
    first = write(tmp_path, "a.csv", f"{HEADER}\nTCS,{TCS},2024-03-14,4000.00,4050.00,3990.00,4020.00,500000\n")
    second = write(tmp_path, "b.csv", f"{HEADER}\nTCS,{TCS},2024-03-14,4000.00,4050.00,3990.00,4030.00,500000\n")
    ingest_price_file(conn, SOURCE, first, RETRIEVED, raw_dir=tmp_path / "raw")
    report = ingest_price_file(conn, SOURCE, second, "2024-03-15T20:00:00+05:30", raw_dir=tmp_path / "raw")
    assert report["quarantined_by_stage"] == {"cross_source_consistency": 1}
    assert conn.execute("SELECT close_price FROM trusted_prices").fetchall() == [(4020.0,)]


def test_same_fact_from_a_second_file_adds_provenance_only(conn, tmp_path):
    row = f"TCS,{TCS},2024-03-14,4000.00,4050.00,3990.00,4020.00,500000"
    first = write(tmp_path, "a.csv", f"{HEADER}\n{row}\n")
    second = write(tmp_path, "b.csv", f"{HEADER}\n{row}\n\n")  # different bytes, same fact
    ingest_price_file(conn, SOURCE, first, RETRIEVED, raw_dir=tmp_path / "raw")
    report = ingest_price_file(conn, SOURCE, second, "2024-03-15T20:00:00+05:30", raw_dir=tmp_path / "raw")
    assert (report["rows_trusted"], report["rows_duplicate"]) == (0, 1)
    assert count(conn, "trusted_prices") == 1
    assert count(conn, "price_provenance") == 2


# ---- whole-file refusals: nothing is stored ----

def test_empty_file_is_refused_and_nothing_is_stored(conn, tmp_path):
    path = write(tmp_path, "empty.csv", HEADER + "\n")
    with pytest.raises(NoDataError):
        ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")
    assert count(conn, "raw_artifacts") == 0
    assert not (tmp_path / "raw").exists()


def test_wrong_columns_are_refused_and_nothing_is_stored(conn, tmp_path):
    path = write(tmp_path, "bad.csv", "symbol,isin,date,close\nTCS,INE467B01029,2024-03-14,4020\n")
    with pytest.raises(TrustChainError):
        ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")
    assert count(conn, "raw_artifacts") == 0


def test_unregistered_source_is_refused(conn, tmp_path):
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    with pytest.raises(SourceRegistryError):
        ingest_price_file(conn, "some_random_site", path, RETRIEVED, raw_dir=tmp_path / "raw")
    assert count(conn, "raw_artifacts") == 0


def test_same_file_twice_is_refused(conn, tmp_path):
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")
    with pytest.raises(ArtifactError):
        ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")
    assert count(conn, "ingestion_runs") == 1


def test_publication_time_without_evidence_is_refused(conn, tmp_path):
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    with pytest.raises(ArtifactError):
        ingest_price_file(conn, SOURCE, path, RETRIEVED, published_at=RETRIEVED, raw_dir=tmp_path / "raw")
    assert count(conn, "raw_artifacts") == 0


def test_failure_midway_leaves_nothing_behind(conn, tmp_path, monkeypatch):
    def broken(rec):
        raise RuntimeError("simulated crash")
    monkeypatch.setattr(trust_chain, "check_anomalies", broken)
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    with pytest.raises(RuntimeError):
        ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")
    for table in ("raw_artifacts", "ingestion_runs", "quarantine", "trusted_prices", "price_provenance"):
        assert count(conn, table) == 0, table


# ---- 40A item 11: provenance to the raw bytes ----

def test_every_trusted_fact_resolves_to_a_raw_artifact_hash(conn, tmp_path):
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")
    rows = conn.execute(
        "SELECT t.price_id, a.sha256, a.stored_path FROM trusted_prices t"
        " JOIN price_provenance p ON p.price_id = t.price_id"
        " JOIN ingestion_runs r ON r.run_id = p.run_id"
        " JOIN raw_artifacts a ON a.artifact_id = r.artifact_id"
    ).fetchall()
    assert {r[0] for r in rows} == {r[0] for r in conn.execute("SELECT price_id FROM trusted_prices")}
    for _, sha, stored in rows:
        assert hashlib.sha256(Path(stored).read_bytes()).hexdigest() == sha
    assert Path(rows[0][2]).read_bytes() == path.read_bytes()  # kept byte-for-byte


# ---- 5B: availability of trusted prices ----

def test_trusted_price_availability_follows_5b(conn, tmp_path):
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    ingest_price_file(conn, SOURCE, path, RETRIEVED, raw_dir=tmp_path / "raw")
    price_id = conn.execute("SELECT price_id FROM trusted_prices WHERE isin = ?", [TCS]).fetchone()[0]
    after = "2024-03-16T10:00:00+05:30"
    before = "2024-03-15T12:00:00+05:30"
    assert price_availability(conn, price_id, after, PitClaim.CURRENT_DECISION) == Availability.ELIGIBLE
    assert price_availability(conn, price_id, before, PitClaim.CURRENT_DECISION) == Availability.NOT_ELIGIBLE
    # Dated 2024-03-14, retrieved before the decision - but publication never proven.
    assert price_availability(conn, price_id, after, PitClaim.HISTORICAL_REPLAY) == Availability.AVAILABILITY_REVIEW


def test_proven_publication_makes_replay_eligible(conn, tmp_path):
    path = write(tmp_path, "prices.csv", CORRUPTED_FILE)
    ingest_price_file(conn, SOURCE, path, RETRIEVED, published_at="2024-03-14T18:00:00+05:30",
                      publication_evidence="exchange archive timestamp, checked by hand",
                      raw_dir=tmp_path / "raw")
    price_id = conn.execute("SELECT price_id FROM trusted_prices WHERE isin = ?", [TCS]).fetchone()[0]
    decision = "2024-03-15T09:00:00+05:30"
    assert price_availability(conn, price_id, decision, PitClaim.HISTORICAL_REPLAY) == Availability.ELIGIBLE


# ---- stage order and strict typing ----

def test_stages_run_in_the_architecture_order():
    assert [s.value for s in TrustStage] == [
        "schema_and_type",
        "timestamp_and_availability",
        "entity_resolution",
        "deduplication",
        "cross_source_consistency",
        "anomaly_detection",
    ]


@pytest.mark.parametrize("bad_close", ["1,234.50", "-5", "12.3.4", "1e3", "Rs 100"])
def test_numbers_are_never_guessed(bad_close):
    row = {"symbol": "TCS", "isin": TCS, "trade_date": "2024-03-14", "open": "1",
           "high": "2", "low": "1", "close": bad_close, "volume": "10"}
    with pytest.raises(RecordRejected) as rejected:
        check_schema_and_type(row)
    assert rejected.value.stage == TrustStage.SCHEMA_AND_TYPE


@pytest.mark.parametrize("prices", [("0", "2", "0", "1"), ("1", "2", "1", "3"), ("1.5", "2", "1.6", "1.8")])
def test_impossible_prices_are_anomalies(prices):
    o, h, l, c = prices
    rec = check_schema_and_type({"symbol": "TCS", "isin": TCS, "trade_date": "2024-03-14", "open": o,
                                 "high": h, "low": l, "close": c, "volume": "10"})
    with pytest.raises(RecordRejected) as rejected:
        trust_chain.check_anomalies(rec)
    assert rejected.value.stage == TrustStage.ANOMALY_DETECTION


@pytest.mark.parametrize("bad_date", ["14-03-2024", "2024-02-30", "2024/03/14"])
def test_dates_are_never_guessed(bad_date):
    row = {"symbol": "TCS", "isin": TCS, "trade_date": bad_date, "open": "1",
           "high": "2", "low": "1", "close": "1.5", "volume": "10"}
    with pytest.raises(RecordRejected):
        check_schema_and_type(row)


def test_stage_4_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_04_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_PRICE_TRUST_CHAIN_BASELINE"
    assert record["not_claimed"]["real NSE files ingested"] is False
