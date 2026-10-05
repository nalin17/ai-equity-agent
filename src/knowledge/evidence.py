"""The point-in-time evidence object: every information domain normalised to one shape (architecture 40B step 11,
3B, 3C, 4A rule 5, 4C, 4D, 4E, 5B, 30A; ADR-012).

One Evidence is one piece of information as it stood at a decision time under a claim (5B.2):
  evidence_id    the stored row it comes from ('<table>:<key>'), so every claim made later can cite its fact
                 record (40B step 14)
  domain         an information domain of 3B (with 3C ownership and flows)
  kind           what it is inside the domain: daily_price, reported_figure, corporate_announcement, ...
  subject        an ISIN for evidence about that security, or 'context:<scope>' for markets, the economy and
                 the world (3B rule 4) - context is never a covered security, target or benchmark (3G)
  attribution    DIRECT - the security's own record; ROUTE - an event without an issuer reaching the security
                 through declared, recorded routes, named in routes (4A rule 5); CONTEXT - about no security
  observed       the day the information is about (trade date, period end, day it happened) - never its
                 availability (5B.1)
  available_at   what proves availability under the claim: this system's retrieval for current-decision use,
                 the source's proven publication time for historical replay (5B.2); never after the decision
  value          a number or a text; or None with its missing-data class - the no-data sentinel is never
                 confused with a value (4C rule 1, 4C.1 rule 3)
  extraction_confidence  how sure the reading of a text is (40B step 9) - a registered reading, never an
                 investment confidence; None where nothing was read from text
Texts are data, never instructions (4D).

An EvidenceGap says what could not be given and why (4E rule 2; the missing set of 30A.2): a domain with no
adapter yet, evidence withheld for want of proven availability, a component that could not run, trading days
with no file, or evidence deliberately left out with the reason (30A.1 rule 3).
"""
import math
import re
from dataclasses import dataclass, field
from enum import StrEnum

from core.dates import strict_iso_date
from data_quality.extraction_confidence import ExtractionConfidence
from data_quality.missing_data import MissingClass
from provenance.availability import PitClaim, TimestampError, parse_timestamp
from universe.entities import InvalidIsinError, validate_isin


class Domain(StrEnum):   # 3B and 3C
    MARKET = "market"
    FUNDAMENTAL = "fundamental"
    CORPORATE_EVENTS = "corporate_events"
    NEWS_EXTERNAL = "news_external"
    PUBLIC_SENTIMENT = "public_sentiment"
    SECTOR_MACRO = "sector_macro"
    OWNERSHIP_FLOWS = "ownership_flows"
    DERIVATIVES_POSITIONING = "derivatives_positioning"
    ALTERNATIVE_DATA = "alternative_data"


class Attribution(StrEnum):
    DIRECT = "direct"
    ROUTE = "route"
    CONTEXT = "context"


class GapNature(StrEnum):
    NOT_BUILT = "not_built"          # the domain has no adapter yet
    WITHHELD = "withheld"            # stored, but availability not proven under this claim (5B.1)
    DEGRADED = "degraded"            # a component could not run (4E)
    MISSING = "missing"              # expected and absent, with its missing-data class (4C)
    EXCLUDED = "excluded"            # deliberately left out, with the reason (30A.1 rule 3)


ISSUER_DOMAINS = frozenset({Domain.MARKET, Domain.FUNDAMENTAL, Domain.CORPORATE_EVENTS})   # always one security
CONTEXT = "context:"
SCOPE = re.compile(r"^context:[a-z0-9_]+(:[A-Za-z0-9_.-]+)*$")
KIND = re.compile(r"^[a-z][a-z_]*$")
TABLE_KEY = re.compile(r"^[a-z][a-z_]*:\S+$")


class EvidenceError(ValueError):
    """An evidence record or gap breaks a rule of the evidence object; it is refused, never repaired."""


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    domain: Domain
    kind: str
    subject: str
    attribution: Attribution
    observed: str
    available_at: str
    claim: PitClaim
    value: object
    unit: str | None
    source_id: str
    missing_class: MissingClass | None = None
    value_text: str | None = None
    extraction_confidence: ExtractionConfidence | None = None
    routes: tuple = ()
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        def fix(name, kind):
            value = getattr(self, name)
            try:
                object.__setattr__(self, name, None if value is None else kind(value))
            except ValueError:
                raise EvidenceError(f"{self.evidence_id}: {name} {value!r} is not a registered {kind.__name__}") from None
        if not isinstance(self.evidence_id, str) or not TABLE_KEY.match(self.evidence_id):
            raise EvidenceError(f"evidence_id {self.evidence_id!r} must name its stored row as '<table>:<key>'")
        for name, kind in (("domain", Domain), ("attribution", Attribution), ("claim", PitClaim),
                           ("missing_class", MissingClass), ("extraction_confidence", ExtractionConfidence)):
            if name in ("domain", "attribution", "claim") and getattr(self, name) is None:
                raise EvidenceError(f"{self.evidence_id}: {name} is required")
            fix(name, kind)
        if not isinstance(self.kind, str) or not KIND.match(self.kind):
            raise EvidenceError(f"{self.evidence_id}: kind {self.kind!r} is not a lower-case name")
        if not isinstance(self.source_id, str) or not self.source_id:
            raise EvidenceError(f"{self.evidence_id}: source_id is required")
        _check_subject(self)
        try:
            strict_iso_date(self.observed)
        except (TypeError, ValueError):
            raise EvidenceError(f"{self.evidence_id}: observed {self.observed!r} is not a YYYY-MM-DD date") from None
        try:
            parse_timestamp(self.available_at)
        except TimestampError as e:
            raise EvidenceError(f"{self.evidence_id}: available_at - {e}") from None
        _check_value(self)
        object.__setattr__(self, "routes", tuple(self.routes))


def _check_subject(e):
    if e.subject.startswith(CONTEXT):
        if not SCOPE.match(e.subject):
            raise EvidenceError(f"{e.evidence_id}: context subject {e.subject!r} is not 'context:<scope>'")
        if e.domain in ISSUER_DOMAINS:
            raise EvidenceError(f"{e.evidence_id}: {e.domain} evidence is always about one security, never context")
        if e.attribution != Attribution.CONTEXT or e.routes:
            raise EvidenceError(f"{e.evidence_id}: context evidence is attributed to no security")
        return
    try:
        validate_isin(e.subject)
    except InvalidIsinError:
        raise EvidenceError(f"{e.evidence_id}: subject {e.subject!r} is neither an ISIN nor 'context:<scope>'") from None
    if e.attribution == Attribution.CONTEXT:
        raise EvidenceError(f"{e.evidence_id}: evidence about {e.subject} cannot be attributed as context")
    if e.attribution == Attribution.ROUTE and (not e.routes or e.domain in ISSUER_DOMAINS):
        raise EvidenceError(f"{e.evidence_id}: an event without an issuer reaches a security only through"
                            " declared, recorded routes (4A rule 5)")
    if e.attribution == Attribution.DIRECT and e.routes:
        raise EvidenceError(f"{e.evidence_id}: the security's own evidence travels no route")


def _check_value(e):
    if e.value is None:
        if e.missing_class is None:
            raise EvidenceError(f"{e.evidence_id}: an absent value needs its missing-data class (4C rule 1)")
        return
    if e.missing_class is not None:
        raise EvidenceError(f"{e.evidence_id}: a value cannot also carry a missing-data class")
    if isinstance(e.value, bool) or not isinstance(e.value, (int, float, str)):
        raise EvidenceError(f"{e.evidence_id}: value must be a number or a text, not {type(e.value).__name__}")
    if isinstance(e.value, float) and not math.isfinite(e.value):
        raise EvidenceError(f"{e.evidence_id}: value {e.value} is not a finite number")
    if isinstance(e.value, str) and not e.value.strip():
        raise EvidenceError(f"{e.evidence_id}: an empty text is not a value")


@dataclass(frozen=True)
class EvidenceGap:
    domain: Domain
    nature: GapNature
    component: str
    reason: str
    count: int | None = None
    items: tuple = ()          # dates or keys, never values
    missing_class: MissingClass | None = None

    def __post_init__(self):
        try:
            object.__setattr__(self, "domain", Domain(self.domain))
            object.__setattr__(self, "nature", GapNature(self.nature))
            if self.missing_class is not None:
                object.__setattr__(self, "missing_class", MissingClass(self.missing_class))
        except ValueError as e:
            raise EvidenceError(f"gap {self.component!r}: {e}") from None
        if not self.component or not self.reason:
            raise EvidenceError("a gap names its component and its reason")
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True)
class Bundle:
    """Everything the hub could give for one subject at one decision time under one claim."""
    subject: str | None
    decision_time: str
    claim: PitClaim
    start: str
    end: str
    window_note: str | None
    evidence: tuple
    gaps: tuple
    hub_version: str

    def __post_init__(self):
        decision = parse_timestamp(self.decision_time)
        late = [e.evidence_id for e in self.evidence if parse_timestamp(e.available_at) > decision]
        if late:   # fail closed: an adapter leaked evidence from after the decision
            raise EvidenceError(f"evidence available after the decision time: {late[:3]}")
        wrong = [e.evidence_id for e in self.evidence if e.claim != self.claim]
        if wrong:
            raise EvidenceError(f"evidence judged under another claim: {wrong[:3]}")

    def of(self, domain):
        return [e for e in self.evidence if e.domain == Domain(domain)]

    def gaps_of(self, domain):
        return [g for g in self.gaps if g.domain == Domain(domain)]

    def counts(self):
        """{domain: number of evidence records} for every domain of 3B and 3C, zero included."""
        return {d: len(self.of(d)) for d in Domain}


def withheld(domain, component, count, reason):
    return EvidenceGap(domain, GapNature.WITHHELD, component, reason, count=count)
