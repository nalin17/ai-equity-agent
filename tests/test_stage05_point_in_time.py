"""Stage 5 acceptance tests: point-in-time facts and provenance.

40A item 12 / 40B step 4: write a fact, correct it a week later, query as of a
prior knowledge date, get the original value.
47A guardrail 2: no silent rewriting of history - restatements append, never
overwrite (enforced by the database itself).
4C rule 1 / criterion 32: a null without a missing-data class is rejected at
write time.
5B: replay needs proven publication; unknown never defaults to eligible.
"""
import re
import sqlite3

import pytest

from core.config import PROJECT_ROOT
from core.database import connect, migrate, rollback
from data_quality.missing_data import MissingDataError
from ingestion.source_registry import sync_sources
from provenance.availability import Availability, PitClaim
from provenance.pit_store import (
    PitConflictError,
    PitError,
    fact_as_of,
    record_correction,
    record_fact,
)
from provenance.raw_store import store_raw_artifact
from universe.entities import add_entity

TCS = "INE467B01029"
KEY = (TCS, "revenue", "consolidated", "2024-03-31")
SOURCE = "nse_corporate_actions"  # any registered source; the file content is irrelevant here
CURRENT = PitClaim.CURRENT_DECISION
REPLAY = PitClaim.HISTORICAL_REPLAY


@pytest.fixture
def conn():
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    add_entity(c, TCS, "Tata Consultancy Services Limited")
    yield c
    c.close()


@pytest.fixture
def artifact(conn, tmp_path):
    """Make a raw artifact retrieved at a given time (and optionally proven published)."""
    counter = iter(range(1000))

    def make(retrieved_at, published_at=None):
        n = next(counter)
        path = tmp_path / f"filing_{n}.txt"
        path.write_text(f"filing number {n}", encoding="utf-8")
        evidence = "exchange filing timestamp, checked by hand" if published_at else None
        artifact_id, _ = store_raw_artifact(conn, SOURCE, path, retrieved_at, published_at, evidence,
                                            raw_dir=tmp_path / "raw")
        return artifact_id

    return make


def count(c):
    return c.execute("SELECT COUNT(*) FROM pit_facts").fetchone()[0]


# ---- 40A item 12: the acceptance test ----

def test_correction_a_week_later_does_not_change_the_past(conn, artifact):
    original = artifact("2024-05-01T18:00:00+05:30")
    corrected = artifact("2024-05-08T18:00:00+05:30")
    record_fact(conn, *KEY, 1000.0, "INR_crore", original)
    record_correction(conn, *KEY, 1050.0, "INR_crore", corrected,
                      evidence="restated in the next quarter's filing")

    before = fact_as_of(conn, *KEY, "2024-05-03T10:00:00+05:30", CURRENT)
    after = fact_as_of(conn, *KEY, "2024-05-10T10:00:00+05:30", CURRENT)
    too_early = fact_as_of(conn, *KEY, "2024-04-30T10:00:00+05:30", CURRENT)

    assert (before.availability, before.value, before.version) == (Availability.ELIGIBLE, 1000.0, 1)
    assert (after.availability, after.value, after.version) == (Availability.ELIGIBLE, 1050.0, 2)
    assert too_early.availability == Availability.NOT_ELIGIBLE and too_early.value is None
    # Negative assertion: the original row is still there, unchanged.
    rows = conn.execute("SELECT version, value FROM pit_facts ORDER BY version").fetchall()
    assert rows == [(1, 1000.0), (2, 1050.0)]


# ---- guardrail 2: history is append-only, enforced by the database ----

@pytest.mark.parametrize("sql", [
    "UPDATE pit_facts SET value = 1",
    "DELETE FROM pit_facts",
    "UPDATE raw_artifacts SET sha256 = 'x'",
    "DELETE FROM raw_artifacts",
])
def test_history_cannot_be_rewritten_or_deleted(conn, artifact, sql):
    record_fact(conn, *KEY, 1000.0, "INR_crore", artifact("2024-05-01T18:00:00+05:30"))
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute(sql)
    assert conn.execute("SELECT value FROM pit_facts").fetchall() == [(1000.0,)]


@pytest.mark.parametrize("table", ["trusted_prices", "quarantine", "price_provenance"])
def test_stage_4_tables_are_append_only_too(conn, table):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    assert {f"{table}_no_update", f"{table}_no_delete"} <= names


def test_no_code_updates_or_deletes_history():
    # 40D-style static check: nothing in src/ even tries.
    pattern = re.compile(
        r"(UPDATE|DELETE\s+FROM)\s+(pit_facts|raw_artifacts|trusted_prices|quarantine|price_provenance)\b",
        re.IGNORECASE,
    )
    offenders = [str(p) for p in (PROJECT_ROOT / "src").rglob("*.py")
                 if pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


# ---- 4C rule 1: nulls always carry a class ----

def test_null_without_class_is_rejected_by_the_code(conn, artifact):
    with pytest.raises(MissingDataError):
        record_fact(conn, *KEY, None, "INR_crore", artifact("2024-05-01T18:00:00+05:30"))
    assert count(conn) == 0


def test_null_without_class_is_rejected_by_the_database(conn, artifact):
    artifact_id = artifact("2024-05-01T18:00:00+05:30")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO pit_facts (isin, field, basis, period_end, unit, value, missing_class, version,"
            " artifact_id, recorded_at) VALUES (?, 'revenue', 'consolidated', '2024-03-31', 'INR_crore',"
            " NULL, NULL, 1, ?, '2024-05-01')",
            [TCS, artifact_id],
        )


def test_missing_value_with_class_is_stored_and_returned(conn, artifact):
    record_fact(conn, *KEY, None, "INR_crore", artifact("2024-05-01T18:00:00+05:30"),
                missing_class="not_disclosed")
    result = fact_as_of(conn, *KEY, "2024-05-02T10:00:00+05:30", CURRENT)
    assert (result.value, result.missing_class) == (None, "not_disclosed")


def test_extraction_failure_can_be_corrected_to_a_value_with_evidence(conn, artifact):
    record_fact(conn, *KEY, None, "INR_crore", artifact("2024-05-01T18:00:00+05:30"),
                missing_class="extraction_failure")
    record_correction(conn, *KEY, 1000.0, "INR_crore", artifact("2024-05-02T18:00:00+05:30"),
                      evidence="parser fixed; value read from page 3 of the filing")
    assert fact_as_of(conn, *KEY, "2024-05-03T10:00:00+05:30", CURRENT).value == 1000.0


# ---- conflicts and corrections ----

def test_same_value_again_is_the_same_fact(conn, artifact):
    first = record_fact(conn, *KEY, 1000.0, "INR_crore", artifact("2024-05-01T18:00:00+05:30"))
    again = record_fact(conn, *KEY, 1000.0, "INR_crore", artifact("2024-05-02T18:00:00+05:30"))
    assert first == again and count(conn) == 1


def test_different_value_without_correction_is_a_conflict(conn, artifact):
    record_fact(conn, *KEY, 1000.0, "INR_crore", artifact("2024-05-01T18:00:00+05:30"))
    with pytest.raises(PitConflictError):
        record_fact(conn, *KEY, 1100.0, "INR_crore", artifact("2024-05-02T18:00:00+05:30"))
    assert count(conn) == 1


def test_bad_corrections_are_refused(conn, artifact):
    early = artifact("2024-04-01T18:00:00+05:30")
    record_fact(conn, *KEY, 1000.0, "INR_crore", artifact("2024-05-01T18:00:00+05:30"))
    later = artifact("2024-05-08T18:00:00+05:30")
    with pytest.raises(PitError, match="evidence"):
        record_correction(conn, *KEY, 1050.0, "INR_crore", later, evidence="")
    with pytest.raises(PitError, match="same value"):
        record_correction(conn, *KEY, 1000.0, "INR_crore", later, evidence="x")
    with pytest.raises(PitError, match="known before"):
        record_correction(conn, *KEY, 1050.0, "INR_crore", early, evidence="x")
    with pytest.raises(PitError, match="Unit change"):
        record_correction(conn, *KEY, 10500.0, "INR_lakh", later, evidence="x")
    assert count(conn) == 1


def test_cannot_correct_what_was_never_recorded(conn, artifact):
    with pytest.raises(PitError, match="Nothing to correct"):
        record_correction(conn, *KEY, 1050.0, "INR_crore", artifact("2024-05-08T18:00:00+05:30"), "x")


def test_consolidated_and_standalone_never_mix(conn, artifact):
    a = artifact("2024-05-01T18:00:00+05:30")
    record_fact(conn, TCS, "revenue", "consolidated", "2024-03-31", 1000.0, "INR_crore", a)
    record_fact(conn, TCS, "revenue", "standalone", "2024-03-31", 800.0, "INR_crore", a)
    t = "2024-05-02T10:00:00+05:30"
    assert fact_as_of(conn, TCS, "revenue", "consolidated", "2024-03-31", t, CURRENT).value == 1000.0
    assert fact_as_of(conn, TCS, "revenue", "standalone", "2024-03-31", t, CURRENT).value == 800.0


@pytest.mark.parametrize("key", [
    ("INE009A01021", "revenue", "consolidated", "2024-03-31", "INR_crore"),  # company not loaded
    (TCS, "Revenue ", "consolidated", "2024-03-31", "INR_crore"),           # bad field name
    (TCS, "revenue", "group", "2024-03-31", "INR_crore"),                   # unknown basis
    (TCS, "revenue", "consolidated", "31-03-2024", "INR_crore"),            # bad date
    (TCS, "revenue", "consolidated", "2024-03-31", "rupees"),               # unknown unit
])
def test_badly_keyed_facts_are_refused(conn, artifact, key):
    isin, field, basis, period_end, unit = key
    with pytest.raises(PitError):
        record_fact(conn, isin, field, basis, period_end, 1.0, unit, artifact("2024-05-01T18:00:00+05:30"))
    assert count(conn) == 0


# ---- 5B: historical replay needs proven publication ----

def test_replay_without_proven_publication_is_review(conn, artifact):
    record_fact(conn, *KEY, 1000.0, "INR_crore", artifact("2024-05-01T18:00:00+05:30"))
    result = fact_as_of(conn, *KEY, "2024-06-01T10:00:00+05:30", REPLAY)
    assert result.availability == Availability.AVAILABILITY_REVIEW and result.value is None


def test_replay_is_review_when_a_later_correction_has_unproven_publication(conn, artifact):
    record_fact(conn, *KEY, 1000.0, "INR_crore",
                artifact("2024-05-01T18:00:00+05:30", published_at="2024-05-01T16:00:00+05:30"))
    record_correction(conn, *KEY, 1050.0, "INR_crore", artifact("2024-05-08T18:00:00+05:30"),
                      evidence="restated")
    # The correction might already have been public on 2024-05-05 - we cannot prove otherwise.
    assert fact_as_of(conn, *KEY, "2024-05-05T10:00:00+05:30", REPLAY).availability == \
        Availability.AVAILABILITY_REVIEW
    # For a current decision, only our own retrieval time matters.
    assert fact_as_of(conn, *KEY, "2024-05-05T10:00:00+05:30", CURRENT).value == 1000.0


def test_replay_with_both_publications_proven(conn, artifact):
    record_fact(conn, *KEY, 1000.0, "INR_crore",
                artifact("2024-05-01T18:00:00+05:30", published_at="2024-05-01T16:00:00+05:30"))
    record_correction(conn, *KEY, 1050.0, "INR_crore",
                      artifact("2024-05-08T18:00:00+05:30", published_at="2024-05-08T16:00:00+05:30"),
                      evidence="restated")
    assert fact_as_of(conn, *KEY, "2024-05-05T10:00:00+05:30", REPLAY).value == 1000.0
    assert fact_as_of(conn, *KEY, "2024-05-09T10:00:00+05:30", REPLAY).value == 1050.0


# ---- 40A item 11: provenance ----

def test_every_fact_resolves_to_its_raw_artifact_hash(conn, artifact):
    artifact_id = artifact("2024-05-01T18:00:00+05:30")
    record_fact(conn, *KEY, 1000.0, "INR_crore", artifact_id)
    sha = conn.execute("SELECT sha256 FROM raw_artifacts WHERE artifact_id = ?", [artifact_id]).fetchone()[0]
    assert fact_as_of(conn, *KEY, "2024-05-02T10:00:00+05:30", CURRENT).artifact_sha256 == sha
    orphans = conn.execute(
        "SELECT COUNT(*) FROM pit_facts f LEFT JOIN raw_artifacts a ON a.artifact_id = f.artifact_id"
        " WHERE a.sha256 IS NULL"
    ).fetchone()[0]
    assert orphans == 0


def test_fact_without_a_source_file_is_refused(conn):
    with pytest.raises(PitError, match="source file"):
        record_fact(conn, *KEY, 1000.0, "INR_crore", 999)


# ---- migration and acceptance record ----

def test_pit_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 4)
    assert c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger'").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'pit_facts'").fetchone()[0] == 0
    c.close()


def test_stage_5_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_05_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_POINT_IN_TIME_FACTS_BASELINE"
    assert record["not_claimed"]["real filings ingested"] is False
