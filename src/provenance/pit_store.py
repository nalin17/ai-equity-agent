"""Point-in-time fact store (architecture Sections 5, 5B, 4C, 40A item 12, 40B step 4).

Historical research must reconstruct what was knowable at time T.

- A fact is identified by: company (ISIN), field, basis, period end.
  Basis is explicit on every fact - consolidated and standalone never mix.
- A fact is never changed. A correction (for example a restated result) is a
  NEW version that supersedes the previous one and cites its evidence. The
  database refuses UPDATE and DELETE on this table.
- When a version became known comes from its raw artifact: our retrieval
  time, and the publication time only where it is proven.
- fact_as_of() answers "what did we know at decision time T?" under either
  point-in-time claim (5B.2). If a later version's availability is unproven,
  the answer is AVAILABILITY_REVIEW - unknown never defaults to eligible.
- A different value arriving for an existing fact WITHOUT being declared a
  correction is a conflict and is refused (Section 4: never resolved by recency).
"""
import re
from dataclasses import dataclass

from core.database import now_utc
from core.dates import strict_iso_date
from data_quality.missing_data import check_reclassification, check_value
from provenance.availability import Availability, disposition, parse_timestamp

BASES = {"consolidated", "standalone", "security"}
UNITS = {"INR", "INR_lakh", "INR_crore", "shares", "ratio", "percent", "count"}
FIELD_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class PitError(Exception):
    """A fact or correction breaks the point-in-time rules."""


class PitConflictError(PitError):
    """A different value arrived for an existing fact without being declared a correction."""


@dataclass(frozen=True)
class PitResult:
    availability: Availability
    value: float | None = None
    missing_class: str | None = None
    version: int | None = None
    fact_id: int | None = None
    artifact_sha256: str | None = None


def _check_key(conn, isin, field, basis, period_end, unit):
    if not conn.execute("SELECT 1 FROM entities WHERE isin = ?", [isin]).fetchone():
        raise PitError(f"No entity with ISIN {isin}")
    if not FIELD_NAME.match(field or ""):
        raise PitError(f"field must be lower_snake_case, got {field!r}")
    if basis not in BASES:
        raise PitError(f"basis must be one of {sorted(BASES)}, got {basis!r}")
    if unit not in UNITS:
        raise PitError(f"unit must be one of {sorted(UNITS)}, got {unit!r}")
    try:
        strict_iso_date(period_end)
    except (TypeError, ValueError):
        raise PitError(f"period_end must be YYYY-MM-DD, got {period_end!r}") from None


def _artifact_retrieved_at(conn, artifact_id):
    row = conn.execute("SELECT retrieved_at FROM raw_artifacts WHERE artifact_id = ?", [artifact_id]).fetchone()
    if row is None:
        raise PitError(f"Unknown raw artifact {artifact_id}; every fact needs its source file")
    return parse_timestamp(row[0])


def _versions(conn, isin, field, basis, period_end):
    rows = conn.execute(
        "SELECT f.fact_id, f.version, f.value, f.missing_class, f.unit,"
        " a.retrieved_at, a.published_at, a.sha256"
        " FROM pit_facts f JOIN raw_artifacts a ON a.artifact_id = f.artifact_id"
        " WHERE f.isin = ? AND f.field = ? AND f.basis = ? AND f.period_end = ?"
        " ORDER BY f.version",
        [isin, field, basis, period_end],
    ).fetchall()
    keys = ("fact_id", "version", "value", "missing_class", "unit", "retrieved_at", "published_at", "sha256")
    return [dict(zip(keys, r)) for r in rows]


def _insert(conn, isin, field, basis, period_end, unit, value, missing_class,
            version, supersedes, evidence, artifact_id):
    return conn.execute(
        "INSERT INTO pit_facts (isin, field, basis, period_end, unit, value, missing_class, version,"
        " supersedes_fact_id, correction_evidence, artifact_id, recorded_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [isin, field, basis, period_end, unit, value,
         None if missing_class is None else str(missing_class),
         version, supersedes, evidence, artifact_id, now_utc()],
    ).lastrowid


def record_fact(conn, isin, field, basis, period_end, value, unit, artifact_id, missing_class=None):
    """Record the first version of a fact. Returns its fact_id.

    The same value arriving again is the same fact (its existing id is returned).
    A different value is refused: it must be recorded as a correction, with evidence.
    """
    _check_key(conn, isin, field, basis, period_end, unit)
    value, missing_class = check_value(value, missing_class)
    _artifact_retrieved_at(conn, artifact_id)
    versions = _versions(conn, isin, field, basis, period_end)
    if versions:
        latest = versions[-1]
        if (latest["value"], latest["missing_class"], latest["unit"]) == (
            value, None if missing_class is None else str(missing_class), unit
        ):
            return latest["fact_id"]
        raise PitConflictError(
            f"{isin} {field} ({basis}, {period_end}) is already recorded as version {latest['version']}"
            " with a different value. Record a correction with evidence; conflicts are never"
            " resolved by taking the newest value."
        )
    return _insert(conn, isin, field, basis, period_end, unit, value, missing_class,
                   1, None, None, artifact_id)


def record_correction(conn, isin, field, basis, period_end, value, unit, artifact_id,
                      evidence, missing_class=None):
    """Append a new version that supersedes the latest one. Returns its fact_id."""
    _check_key(conn, isin, field, basis, period_end, unit)
    if not evidence or not str(evidence).strip():
        raise PitError("A correction must cite its evidence")
    value, missing_class = check_value(value, missing_class)
    versions = _versions(conn, isin, field, basis, period_end)
    if not versions:
        raise PitError("Nothing to correct: record the original fact first")
    latest = versions[-1]
    if unit != latest["unit"]:
        raise PitError(
            f"Unit change {latest['unit']} -> {unit} is a declared transformation, not a correction"
        )
    if (latest["value"], latest["missing_class"]) == (
        value, None if missing_class is None else str(missing_class)
    ):
        raise PitError("The 'correction' has the same value as the current version")
    if _artifact_retrieved_at(conn, artifact_id) <= parse_timestamp(latest["retrieved_at"]):
        raise PitError("A correction cannot have been known before the version it corrects")
    if latest["missing_class"] is not None and missing_class is not None:
        check_reclassification(latest["missing_class"], missing_class, evidence)
    return _insert(conn, isin, field, basis, period_end, unit, value, missing_class,
                   latest["version"] + 1, latest["fact_id"], str(evidence).strip(), artifact_id)


def fact_as_of(conn, isin, field, basis, period_end, decision_time, claim):
    """What was known about this fact at decision_time, under the given 5B claim."""
    versions = _versions(conn, isin, field, basis, period_end)
    states = [disposition(claim, decision_time, v["retrieved_at"], v["published_at"]) for v in versions]
    eligible = [i for i, s in enumerate(states) if s == Availability.ELIGIBLE]
    if not eligible:
        if Availability.AVAILABILITY_REVIEW in states:
            return PitResult(Availability.AVAILABILITY_REVIEW)
        return PitResult(Availability.NOT_ELIGIBLE)
    last = eligible[-1]
    # A later version whose availability is unproven might already have
    # replaced this one at decision time. We cannot know, so we do not answer.
    if any(s == Availability.AVAILABILITY_REVIEW for s in states[last + 1:]):
        return PitResult(Availability.AVAILABILITY_REVIEW)
    v = versions[last]
    return PitResult(Availability.ELIGIBLE, v["value"], v["missing_class"], v["version"],
                     v["fact_id"], v["sha256"])
