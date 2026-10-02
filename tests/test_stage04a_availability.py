"""Stage 4, part 1: availability disposition (architecture 5B) and the new tables.

5B.1: availability is ELIGIBLE / NOT_ELIGIBLE / AVAILABILITY_REVIEW; unknown
never defaults to eligible (criterion 61).
5B.2: current-decision eligibility never implies historical-replay
eligibility (criterion 62).
"""
import pytest

from core.database import connect, migrate, rollback
from provenance.availability import (
    Availability,
    PitClaim,
    TimestampError,
    disposition,
    parse_timestamp,
)

DECISION = "2024-03-15T16:00:00+05:30"
BEFORE = "2024-03-14T18:30:00+05:30"
AFTER = "2024-03-16T09:00:00+05:30"


def test_exactly_three_availability_states():
    assert {a.value for a in Availability} == {"ELIGIBLE", "NOT_ELIGIBLE", "AVAILABILITY_REVIEW"}


def test_current_decision_uses_our_retrieval_time():
    assert disposition(PitClaim.CURRENT_DECISION, DECISION, BEFORE) == Availability.ELIGIBLE
    assert disposition(PitClaim.CURRENT_DECISION, DECISION, AFTER) == Availability.NOT_ELIGIBLE


def test_replay_without_proven_publication_is_review_never_eligible():
    # Retrieved long before the decision, but publication time never proven.
    assert disposition(PitClaim.HISTORICAL_REPLAY, DECISION, BEFORE) == Availability.AVAILABILITY_REVIEW


def test_replay_with_proven_publication():
    assert disposition(PitClaim.HISTORICAL_REPLAY, DECISION, AFTER, published_at=BEFORE) == Availability.ELIGIBLE
    assert disposition(PitClaim.HISTORICAL_REPLAY, DECISION, AFTER, published_at=AFTER) == Availability.NOT_ELIGIBLE


def test_current_decision_eligibility_never_implies_replay_eligibility():
    current = disposition(PitClaim.CURRENT_DECISION, DECISION, BEFORE)
    replay = disposition(PitClaim.HISTORICAL_REPLAY, DECISION, BEFORE)
    assert current == Availability.ELIGIBLE
    assert replay != Availability.ELIGIBLE


@pytest.mark.parametrize("bad", ["2024-03-15T16:00:00", "2024-03-15", "yesterday", "", None])
def test_timestamps_without_timezone_or_malformed_are_refused(bad):
    with pytest.raises(TimestampError):
        parse_timestamp(bad)


def test_timezones_are_compared_correctly():
    # 10:30 UTC is 16:00 in India - the same instant.
    assert disposition(PitClaim.CURRENT_DECISION, DECISION, "2024-03-15T10:30:00+00:00") == Availability.ELIGIBLE
    assert disposition(PitClaim.CURRENT_DECISION, DECISION, "2024-03-15T10:30:01+00:00") == Availability.NOT_ELIGIBLE


def test_data_trust_tables_migrate_and_roll_back():
    c = connect(":memory:")
    migrate(c)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"raw_artifacts", "ingestion_runs", "quarantine", "trusted_prices", "price_provenance"} <= names
    rollback(c, 3)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "raw_artifacts" not in names and "entities" in names
    c.close()
