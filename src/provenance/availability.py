"""Availability disposition and the two point-in-time claims (architecture 5B).

Core rule: available_at <= decision_time.

Availability is a disposition, not a yes/no:
  ELIGIBLE             proven available by the decision time
  NOT_ELIGIBLE         proven NOT available by the decision time
  AVAILABILITY_REVIEW  not sufficiently proven - never treated as eligible

A trading date does NOT prove when data became available. Neither does a
file timestamp or an assumed end-of-day release time.

Two different claims (5B.2):
  CURRENT_DECISION   data verified and ingested by us may support a decision
                     made after our own retrieval time.
  HISTORICAL_REPLAY  data may support a PAST decision only if its publication
                     time is separately proven. Being dated in the past is not
                     enough. Current-decision eligibility never implies
                     historical-replay eligibility (criterion 62).

This is the single place these vocabularies are defined.
"""
from datetime import datetime
from enum import StrEnum


class Availability(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    AVAILABILITY_REVIEW = "AVAILABILITY_REVIEW"


class PitClaim(StrEnum):
    CURRENT_DECISION = "current_decision"
    HISTORICAL_REPLAY = "historical_replay"


class TimestampError(Exception):
    """A timestamp is missing, malformed or has no timezone."""


def parse_timestamp(value):
    """Parse an ISO timestamp. A timezone is mandatory - '10:00' alone is ambiguous."""
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            raise TimestampError(f"Not an ISO timestamp: {value!r}") from None
    if parsed.tzinfo is None:
        raise TimestampError(f"Timestamp has no timezone: {value!r}")
    return parsed


def disposition(claim, decision_time, retrieved_at, published_at=None):
    """Decide availability of one piece of evidence for one decision time."""
    claim = PitClaim(claim)
    decision_time = parse_timestamp(decision_time)
    if claim == PitClaim.CURRENT_DECISION:
        basis = parse_timestamp(retrieved_at)
    else:
        if published_at is None:
            return Availability.AVAILABILITY_REVIEW
        basis = parse_timestamp(published_at)
    return Availability.ELIGIBLE if basis <= decision_time else Availability.NOT_ELIGIBLE


def price_availability(conn, price_id, decision_time, claim):
    """Availability of a trusted price, using its EARLIEST provenance.

    Current decision: earliest time we retrieved it.
    Historical replay: earliest PROVEN publication time; none proven means review.
    """
    rows = conn.execute(
        "SELECT a.retrieved_at, a.published_at FROM price_provenance p"
        " JOIN ingestion_runs r ON r.run_id = p.run_id"
        " JOIN raw_artifacts a ON a.artifact_id = r.artifact_id"
        " WHERE p.price_id = ?",
        [price_id],
    ).fetchall()
    if not rows:
        return Availability.AVAILABILITY_REVIEW
    retrieved = min(parse_timestamp(r[0]) for r in rows)
    proven = [parse_timestamp(r[1]) for r in rows if r[1] is not None]
    return disposition(claim, decision_time, retrieved, min(proven) if proven else None)
