# AI Self-Learning Equity Research & Market Analysis Agent
## Master Architecture v1.11 — Role-Declared Grounding

Section 30B is replaced. The v1.10 design — parse every numeral, test it for
membership in the injected fact set — is an approach that HKUDS/Vibe-Trading
(34k stars, ~444k LOC, MIT) built, ran and abandoned. Their recorded reason: role was
inferred from the prose around each number against a catalogue of price words, level
words, indicator names and forecast frames, and a catalogue is only as complete as the
day it was typed. The same sentence received opposite verdicts in its two
translations, and every missing phrasing was either a rejected correct answer or a
released fabrication.

The replacement declares role in structured output and verifies per role.

### Change log from v1.10

| # | Change | Section |
|---|---|---|
| ACR-53 | Role-declared figure block replaces prose-inferred numeric verification | 30B.1 |
| ACR-54 | Shape-based, language-independent number classification | 30B.2 |
| ACR-55 | Text normalisation before matching, with offsets mapped back | 30B.2 |
| ACR-56 | Directional rounding band — precision may only narrow | 30B.3 |
| ACR-57 | Identity locked at the agent loop, not only at ingestion | new 30C |
| ACR-58 | Graduated release: correction, redaction, bounded recovery | new 30D |
| ACR-59 | Mechanically-decidable boundary stated explicitly | new 30E |

Adds the six controls identified in the Cloud9 Markets desk review. The pattern is the
same one the Tauric review produced: rules this document already stated are converted
from prose into mechanisms that fail loudly. Two of them replace a model-based check
with a set-membership test, which cannot miss.

### Change log from v1.9

| # | Change | Section |
|---|---|---|
| ACR-45 | Deterministic numeric verification runs before the critic | new 30B |
| ACR-46 | Citation and URL verification against the retrieved set | 30B |
| ACR-47 | Prompt injection defence — ingested content is data, never instruction | new 4D |
| ACR-48 | Model diversity as a correlated-failure control on adversarial pairs | 35A |
| ACR-49 | Least privilege: per-agent tool sets and credential isolation | 35A |
| ACR-50 | Degradation is always disclosed, never silent | new 4E |
| ACR-51 | Inter-agent message audit log | 21 |
| ACR-52 | The API query surface cannot trigger tool calls | 36 |

Derived from a line-by-line review of TauricResearch/TradingAgents (~23k LOC, 77
test files). That project is behind this architecture on statistical validity — it
has no probabilities, therefore no calibration, and no multiple-testing control — but
it is ahead on **enforcement**: its leakage controls were discovered by finding real
leaks in production and each is backed by a test. The six controls below are adapted
from it.

### Change log from v1.8

| # | Change | Section |
|---|---|---|
| ACR-38 | Point-in-time applies to learned knowledge, not only to data | new 6B |
| ACR-39 | Vintage-less vendor fields are withheld from historical runs, not timestamped | new 5A |
| ACR-40 | Date clamping at the tool boundary; the run date is hidden from the model | 5A |
| ACR-41 | Empty vendor results are never cached; explicit no-data sentinel | 4C |
| ACR-42 | REVIEW is distinct from ABSTAIN — unparseable output is not the neutral option | 34 |
| ACR-43 | Architectural rules enforced by static tests, not prose | new 40D |
| ACR-44 | Relevance screening before sentiment aggregation | 4B |

### Change log from v1.7

| # | Change | Section |
|---|---|---|
| ACR-32 | Data Trust pipeline restored as an ordered chain: entity resolution, dedup, cross-source consistency, anomaly detection | 4 |
| ACR-33 | Missing Data Intelligence restored — missing is not one state | new 4C |
| ACR-34 | Sector/macro and alternative data added as information domains | new 3B |
| ACR-35 | Adaptive Evidence Selection as a named pipeline stage | new 30A |
| ACR-36 | Supporting / contradictory / missing evidence triad in the ledger; contradictory-evidence analysis mandatory | 21, 30A |
| ACR-37 | Definition of Success restored as the closing statement | new 49A |

ACR-32 and ACR-33 restore controls that were specified in v1.0, praised in review, and
lost during a later compression. Previous patch passes audited the statistical layer
and did not audit the data layer, so the loss went unnoticed for four revisions. The
audit checklist in 46A is extended accordingly.

### Change log from v1.6

| # | Change | Section |
|---|---|---|
| ACR-28 | Research universe and coverage universe formally separated | new 3A, 14 |
| ACR-29 | Error taxonomy extended: TARGET, EVENT_SURPRISE, COST_EXECUTION, UNKNOWN | 31A |
| ACR-30 | Lifecycle blocking states HELD and REJECTED added | 10 |
| ACR-31 | Summary-document rule: the summary is generated, never edited | 46 |

Breadth thresholds were already specified in section 14 of v1.6 and are unchanged.

Base: v1.4 + v1.5 restoration pass. This revision merges the genuine additions from
the v1.5 document rewrite **as a patch**, so that no previously specified control is
lost.

### Why this is a patch and not a rewrite

Two consecutive full rewrites silently deleted working controls — four at v1.3→v1.4,
twelve at v1.4→v1.5-rewrite, including deflated Sharpe, economic-rationale
preregistration, the effective-N policy, the experiment harness, champion/challenger
and the calibration bin policy. Full rewrites optimise for readability, and the prose
that reads as excessive detail is exactly the set of controls that prevent silent
failure.

**From v1.6 onward, changes are applied as diffs against this base.** New capability
is added as a new section; it does not license regenerating existing ones.

### Change log from v1.5

| # | Change | Section |
|---|---|---|
| ACR-17 | News, announcements and event intelligence as an information domain | new 4A |
| ACR-18 | Public sentiment as an adversarial-input domain | new 4B |
| ACR-19 | Three-way prediction origin: REPLAY / SHADOW_LIVE / PRODUCTION_LIVE | 6A.2, 21 |
| ACR-20 | Event and sentiment feature families added to the tier structure | 9, 12 |
| ACR-21 | Sentiment and event features inherit the Tier C cost gate explicitly | 22A |
| ACR-22 | Shadow-first construction: one end-to-end agent early, specialists underneath | 35A, 40B |
| ACR-23 | Service vs Agent naming discipline | 35A |
| ACR-24 | Implementation sequence from the current codebase, with acceptance tests | new 40B |
| ACR-25 | Component status register — built vs remaining | new 40C |
| ACR-26 | Non-negotiable guardrails consolidated | new 47A |
| ACR-27 | Search-space expansion control tied to domain additions | 25 |

### Change log from v1.4

| # | Change | Section |
|---|---|---|
| ACR-09 | Historical Universe Policy restored — survivorship and delisting | new 6A |
| ACR-10 | Replay-origin vs live-origin separation in the ledger and gates | 6A, 21 |
| ACR-11 | Benchmark Registry restored | new 14A |
| ACR-12 | Error Attribution restored as a platform | new 31A |
| ACR-13 | What counts / does not count as learning restored | new 41A |
| ACR-14 | Transaction-cost policy for Tier C economic evaluation | new 22A |
| ACR-15 | Agent inventory: what is an agent and what is a service | new 35A |
| ACR-16 | Build sequence bound to module-level acceptance tests | 40 |

**Status:** Implementation Baseline  
**Version:** 1.4  
**Purpose:** Build a trustworthy, self-learning equity research and market-analysis system that can evolve its features, models and research hypotheses while preventing leakage, selection bias, self-grading, overfitting and unsupported confidence.

---

## 1. Executive Architecture

```text
External Data Sources
        ↓
Source Registry
        ↓
Data Ingestion
        ↓
Data Quality + Authentication
        ↓
Point-in-Time Data Store
        ↓
Feature Factory
        ↓
Feature Registry
        ↓
Target / Horizon Engine
        ↓
Research & Model Layer
        ↓
Validation Stack
        ↓
Calibration
        ↓
Prediction Ledger
        ↓
Thesis / Market Analysis Engine
        ↓
Abstention + Confidence Gate
        ↓
Simple API
```

Self-learning loop:

```text
Predictions → Outcomes → Scoring → Calibration/Error Analysis
→ Research Opportunities → Controlled Experiments
→ Challengers → Validation → Promotion/Rejection → Production
```

The learning loop must never modify its own scoring definition, calibration target or acceptance criteria.

---

## 2. Core Design Principles

1. Data before models.
2. Every material data point has provenance.
3. Point-in-time correctness is mandatory.
4. No future information may enter a historical prediction.
5. Research and production datasets are separated.
6. Experiments are reproducible and versioned.
7. Autonomous search is controlled because multiple-testing risk grows with experimentation.
8. Backtest returns alone never justify promotion.
9. Confidence must be statistically evaluated and calibrated.
10. The system may abstain when evidence is insufficient.
11. Promotion is explicit and auditable.
12. Holdout data is protected and has a lifecycle.
13. Human oversight remains mandatory for methodology and production promotion.
14. Discovery does not equal promotion.
15. The scoring function, calibration target and acceptance criteria are human-owned artifacts. No learning loop may modify them.
16. Feature hypotheses must be preregistered before evaluation.
17. Feature usefulness is target- and horizon-dependent.

---

## 3. Scope Strategy

Initial vertical slice:

- One exchange
- 30-company focus cohort
- Complete data → feature → analysis → validation → API cycle

The 30-company cohort is **not** the permanent factor-research universe.

Broader point-in-time historical coverage should be used where necessary for robust cross-sectional research. A mature cross-sectional research universe should preferably contain approximately 150–200+ securities when reliable point-in-time data permits.

---

## 3B. Information Domains

Seven domains. Each is separately registered, separately budgeted under 25A, and
separately admitted.

| Domain | Examples | Primary use | Status |
|---|---|---|---|
| Market | Price, volume, volatility, liquidity, corporate-action-adjusted history | Timing, relative strength, risk | Core |
| Fundamental | Statements, earnings, ratios, quality, valuation | Business state | Core |
| Corporate events | Results, guidance, orders, capex, M&A, management change, promoter/insider, ratings, legal | Catalysts and risks | Core (4A) |
| News / external | Company, sector, macro, regulatory, geopolitical, supply chain | Current context | Core (4A) |
| Public sentiment | Attention, discussion volume, crowding | Crowd context | Restricted (4B) |
| Sector / macro | Rates, inflation, commodities, FX, sector flows and regimes | Context and routing | Core |
| Alternative data | Licensed, reproducible, point-in-time sources | Incremental signal | Deferred |

Rules:

1. **Sector/macro is an ingestion domain, not only a regime input.** Commodity input
   costs, rates and FX are direct evidence for specific companies, not merely state
   variables for routing. The Regime Engine consumes this domain; it does not replace it.
2. **Alternative data is deferred and gated on three conditions**: a licence that
   permits research use, point-in-time history that is not reconstructed after the
   fact, and vendor-independent reproducibility. Alternative data that cannot be
   reconstructed as it stood at a past date is unusable here regardless of its
   apparent signal.
3. A new domain is an architecture change request under 25A and brings its own
   experiment budget.

---

## 3A. Two Universes — Research and Coverage

Section 14 requires at least 100 simultaneously eligible securities for
cross-sectional research. Section 3 sets a 30-company focus cohort. These are not in
conflict once they are recognised as two different universes serving two different
purposes, but treating them as one number has consequences for the data build that
must be decided before ingestion starts.

| | Research Universe | Coverage Universe |
|---|---|---|
| Purpose | Feature admission, factor research, calibration statistics, validation | Securities the Equity Research Agent actually produces memos on |
| Size | ≥100 eligible at any point in time; 150–200+ preferred at maturity | 30 initially |
| Depth of data required | Prices, corporate actions, benchmark membership, fundamentals. **Not** filings text, transcripts, or full event extraction | Full depth: filings, transcripts, events, sentiment, provenance to source |
| Survivorship handling | Mandatory point-in-time membership including delisted, merged and suspended names (6A.1) | Same, applied to the cohort |
| Cost of an error | Wrong statistics; silent | Wrong memo; visible |

### 3A.1 Why the split matters for the build

The research universe needs **breadth, not depth**. Validating the statistical layer
on real dependency structures — the standing risk in 40C — requires cross-sectional
price and benchmark data for 100+ names, which is a bulk ingestion problem. It does
not require filings extraction, which is the expensive part.

This means the statistical revalidation can proceed well before the full data
foundation is complete. It is gated on 40B steps 2 through 6 for a wide universe, not
on steps 7 through 11.

### 3A.2 Rules

1. Every effective-N, calibration and feature-admission statistic declares which
   universe produced it. A statistic computed on the coverage universe alone does not
   satisfy section 14 breadth.
2. The coverage universe is a subset of the research universe. A security cannot be
   covered without being eligible.
3. Both universes are point-in-time and survivorship-aware. Neither is a query against
   currently listed names.
4. Widening the coverage universe is a scope decision. Widening the research universe
   is a data-ingestion task and requires no architecture change.
5. A feature admitted on research-universe evidence is not thereby validated for the
   coverage cohort if the cohort differs systematically from the research universe in
   size, liquidity or sector mix. That difference is measured and recorded, not
   assumed away.

---

## 4. Data Trust Platform

### Source Registry

Each source records:

- source_id
- provider
- data type
- endpoint/document reference
- license/usage constraints
- update frequency
- historical coverage
- latency
- revision policy
- reliability rating
- authentication method

### Data Authentication

Distinguish:

```text
Extracted
Validated
Authenticated
Point-in-time valid
Production eligible
```

Authentication means the value passes source, timestamp, schema, reconciliation and plausibility checks.

### The Trust Chain

Trust is produced by an ordered pipeline, not by a set of checks applied in any
order. Each stage may reject or quarantine; none may silently repair.

```text
raw source
→ schema and type check
→ timestamp and availability assignment
→ ENTITY RESOLUTION
→ deduplication
→ corporate action and version check
→ cross-source consistency
→ anomaly detection
→ missing-data classification   (4C)
→ point-in-time control
→ survivorship / universe control   (6A.1)
→ provenance and lineage
→ trusted data
```

### Entity Resolution

Identity is resolved before anything else is computed, because every downstream error
caused by identity is silent.

1. **ISIN is the primary key.** Not the trading symbol. Symbols change on renames,
   demergers, series moves and reconstitutions; keying on symbol corrupts history the
   first time one changes, with no error raised.
2. Symbol, BSE scrip code, vendor identifiers and company name are **aliases**, each
   with `valid_from` and `valid_to`.
3. The resolver accepts any identifier form and returns exactly one entity or raises.
   Ambiguity raises. It never guesses, never picks the best match, never falls back to
   fuzzy name matching in production.
4. Mergers, demergers and renames are entity events with effective dates, not
   overwrites of an existing row.

### Deduplication and cross-source consistency

1. The same fact arriving from two sources is one fact with two provenance records,
   not two facts.
2. Headline financial figures are pulled from two independent sources where available.
   Divergence beyond declared tolerance **halts** the run; it is never averaged,
   preferred by recency, or resolved by source ranking alone.
3. As-reported values traced to a filing are preferred over vendor-normalised values.
4. Unresolved divergence is written to a conflict record and surfaced, not suppressed.

### Anomaly detection

Impossible values, unit errors, stale-but-fresh-looking data, implausible period
changes and broken accounting identities are detected at ingestion. A failing record
is **quarantined**, not corrected. Automatic repair of source data is prohibited —
it destroys the audit trail that provenance exists to provide.

---

## 4D. Ingested Content Is Data, Never Instruction

Every information domain in section 3B is an attacker-writable surface. A filing
footnote, an exchange announcement, a news article and a social post can all contain
instruction-shaped text, and all of them reach an agent's context. Section 4B.2
already treats sentiment as adversarial input; this section generalises that to every
domain and to the instruction channel specifically.

The threat is not hypothetical for this system. A party with a financial interest in
how a security is perceived has a direct incentive to place text designed to steer an
automated reader. Anyone who knows the desk reads exchange announcements can write
into one.

### 4D.1 Rules

1. **All retrieved content is wrapped as data** before it enters any prompt, in a
   delimited block labelled as untrusted source material, never concatenated into an
   instruction.
2. **No retrieved content may alter agent behaviour.** Instructions found inside
   ingested text are reported as an observation about the document, never followed.
   Agent system prompts state this explicitly.
3. **Tool access is not reachable from content.** No agent may invoke a tool, change
   a scope, or widen a permission as a result of text it read. The fixed graph
   (35A) already forbids stage changes; this extends it to tool invocation.
4. **Injection attempts are logged as a data-quality signal.** Detected
   instruction-shaped content in a source is recorded against that source's
   reliability rating in the Source Registry, not silently stripped. Repeated attempts
   from one source are evidence about the source.
5. **Extraction output is validated against a schema** before it becomes a fact. An
   extraction agent that returns prose where a number was expected has failed, whether
   the cause was a bad parse or a successful injection.

### 4D.2 Blast radius

Injection succeeds when a compromised agent can do something. The controls that bound
it are the same ones that bound ordinary error: deterministic numeric verification
(30B), provenance resolution against the fact store, least privilege (35A), and the
scoring machinery being outside every agent's write scope (35). An agent that can only
write prose into a memo, where every number in that prose is independently verified,
is a poor target.

---

## 4C. Missing Data Intelligence

"Missing" is not one state, and collapsing the states below into a null is how a
system produces confident wrong answers. Every absent value is classified:

| Class | Meaning | Correct handling |
|---|---|---|
| `not_applicable` | The concept does not apply to this entity — inventory turnover for a bank | Exclude from the metric; not a gap |
| `not_yet_released` | The period exists, the disclosure is not yet due | Absent by design; horizon-aware |
| `not_disclosed` | Due, and the company chose not to disclose | **Information in itself** — often material |
| `extraction_failure` | Present in the source, this system failed to read it | Defect; enters the triage queue |
| `source_conflict` | Sources disagree and the conflict is unresolved | Blocks use; see cross-source consistency |
| `structurally_absent` | Never existed — pre-listing, pre-incorporation | Bounds the usable history |

Rules:

1. A null is never written without a class. A null without a class is rejected at
   write time.
2. `not_disclosed` is never imputed. Non-disclosure is evidence and is passed to the
   research agent as such.
3. `extraction_failure` never silently degrades to `not_disclosed`. Conflating a bug
   with a company decision is the specific failure this section prevents.
4. Imputation, where permitted at all, is a declared, versioned transformation
   recorded in provenance — never a default applied inside a feature calculation.
5. Missing-data rates by class are monitored. A rising `extraction_failure` rate is a
   data-layer alert, exactly as a rising `unknown` attribution rate is a
   learning-layer alert.

### 4C.1 Empty results are never cached

A transient vendor outage returns nothing. Caching that nothing converts a temporary
failure into permanent fabricated absence, and the resulting gap is then classified
as though the data never existed. This is how a missing-data class gets assigned
wrongly at the point of ingestion, before any of the rules above can help.

1. An empty or zero-row vendor response is **never written to cache**.
2. An empty response raises a typed no-data error rather than returning an empty
   structure. An empty frame passed upward becomes a legitimate-looking absence three
   layers later.
3. Only after every configured vendor is exhausted does the router emit one explicit
   no-data sentinel, which is distinguishable in the evidence record from a value.
4. A cached value carries the fetch timestamp and the vendor that produced it, so a
   stale entry is detectable rather than indistinguishable from a fresh one.

---

## 4E. Degradation Is Disclosed, Never Silent

Optional components fail: a vendor is down, a screening service is unavailable, a
model is rate-limited, an extraction step times out. The run should usually continue —
but the output must say what was missing, and the gap must travel with the claim.

Silent degradation is worse than failure, because the output looks identical to a
complete one and no one can tell later which runs were impaired.

1. Every optional component declares a **degraded mode** and what is lost in it.
   A component with no declared degraded mode is not optional.
2. When a component degrades, the run records a **structured evidence gap**: which
   component, what was unavailable, and over what span.
3. The gap appears in the output contract (37) and in the ledger (21). It is never
   only a log line.
4. A degraded run's claims are **tagged**, and the tag is available to calibration
   analysis so that degraded and complete runs can be scored separately.
5. Abstention (34) triggers when the degradation touches evidence the claim depends
   on. Continuing with a gap is the default; continuing with a gap in load-bearing
   evidence is not.
6. Degradation rates per component are monitored, alongside the `REVIEW`,
   `unknown` and `extraction_failure` rates.

---

## 4A. News, Announcements and Event Intelligence

News is not reduced to a sentiment scalar. The system extracts structured event
records and preserves the underlying text and source for audit.

| Event field | Purpose |
|---|---|
| Identity | Issuer, sector, external entity, event entity |
| Timing | Publication time, source time, effective time, ingestion time |
| Type | Results, guidance, order win, capex, M&A, regulatory, management change, legal, rating |
| Direction | Positive / negative / mixed / uncertain |
| Novelty | New information versus repeated or syndicated coverage |
| Materiality | Potential economic relevance |
| Source quality | Source reliability and authentication state |
| Expected horizon | Short / intermediate / long event-response hypothesis |
| Extraction confidence | Uncertainty of the extraction itself, **separate from investment confidence** |

Rules:

1. Event classification is not evidence that the event causes future returns. Event
   response is a target to be measured, never an assumption.
2. Novelty is computed, not asserted. Syndicated republication of the same release is
   one event, not many, and the duplicate-collapse rule is versioned.
3. Event-response targets (abnormal return, volume or volatility response over a
   defined window) are first-class registered targets subject to the same validation
   stack as any other target.
4. Extraction confidence never propagates into investment confidence. They are stored
   and reported separately.

---

## 4B. Public Sentiment

Sentiment is an evidence feature, never ground truth.

Tracked where available: level, change, velocity, breadth, dispersion, novelty,
attention, crowding.

### 4B.1 Required controls

1. Point-in-time only. Later edits, deletions and retrospective labels cannot enter a
   historical sentiment value.
2. Source quality, automation likelihood and company specificity are scored on
   ingestion.
3. Sentiment is permitted to disagree with fundamentals and events. Disagreement is
   recorded as conflict evidence, not reconciled away.

### 4B.2 Sentiment is adversarial input, not noisy input

This distinction is load-bearing and is the reason sentiment carries stricter
handling than other domains.

Bot-likelihood scoring catches crude automation. It does not catch coordinated
promotion that is designed to look like organic retail interest — which is a
documented and recurring feature of Indian small- and mid-cap markets. Any input that
a third party has a financial incentive to manufacture must be treated as hostile.

Therefore:

1. Sentiment features carry a **liquidity-band restriction**. They are not admitted
   for companies below a declared liquidity or market-capitalisation threshold, where
   manufactured sentiment is cheapest.
2. A sentiment feature may never be the decisive evidence in a claim. It may
   corroborate or contradict; it cannot carry a thesis alone. The Equity Research
   Agent enforces this at synthesis.
3. Abnormal sentiment velocity without a corresponding registered event is flagged as
   a **possible manufactured-signal condition**, and is a reason for abstention rather
   than a directional signal.
4. Sentiment source composition is monitored for concentration. A signal driven by few
   accounts or few venues is reported as such.

### 4B.3 Relevance screening precedes aggregation

Raw post volume for a ticker contains material about other companies, unrelated uses
of the symbol, and posts that mention the company without taking a position on it.
Aggregating them produces a number that measures attention to a string, not sentiment
about a business.

1. Each post is screened before aggregation on two questions: is it about this
   instrument, and does it take a directional position on it.
2. Posts that fail the relevance question are dropped, not down-weighted.
3. The screen is a small calibrated classifier, not the research agent. Screening is
   not analysis.
4. **When screening is unavailable, the evidence block says so explicitly** and the
   unscreened status travels with the feature. It is never silently omitted, and the
   posts are not silently passed through as though screened.
5. Screening pass rates are monitored. A collapsing pass rate usually means symbol
   collision, not a change in sentiment.

---

## 5. Point-in-Time Data Architecture

Historical research must reconstruct what was knowable at time T.

Store:

```text
observation_date
publication_date
effective_date
source_timestamp
revision_timestamp
value
source_id
version
```

A value published after the prediction timestamp cannot enter that historical prediction.

Restated financial statements must not silently replace information available at the original decision date.

---

## 5A. Vintage Enforcement at the Source Boundary

Section 5 assumes a fact can be stamped with when it was true and when it was known.
Some vendor fields cannot be stamped at all, and for those the only safe handling is
refusal.

### 5A.1 Vintage-less fields are withheld, not timestamped

Vendor "company overview" and snapshot endpoints serve present-day values with no
historical vintage: market capitalisation, trailing multiples, 52-week range, TTM
aggregates — and also name, sector and industry, which change on renames and
reclassifications. Stamping such a value with the run date is a lie; stamping it with
today's date and filtering does not help, because the value itself is current.

Rules:

1. Fields with no historical vintage are **withheld entirely** from any run dated in
   the past. They are not approximated, not interpolated, not passed through with a
   warning.
2. The withhold list is a **single shared rule applied at the data layer**, not
   implemented per vendor. Switching provider must not be able to reintroduce the
   leak — which is exactly how this class of leak recurs.
3. Where a historical equivalent exists from a stamped source (market cap computed
   from point-in-time shares outstanding and price), that computed value is used and
   the vendor field stays withheld.
4. A new vendor field defaults to **withheld** until its vintage semantics are
   documented in the Source Registry. Opt-in, not opt-out.

### 5A.2 The run date is enforced, not requested

Any tool that accepts a date is a place where a leak can re-enter, because an agent
can ask for the wrong one.

1. The run date is injected into every dated tool from pipeline state and is
   **excluded from the model-visible schema**. An agent cannot pass it, override it,
   or omit it.
2. Where a tool accepts a caller-supplied date, the effective date is the **earlier**
   of requested and run date. Later requests clamp. Unparseable, empty and missing
   requests fall back to the run date.
3. For a date window, the end clamps to the run date. A window lying entirely after
   the run date is moved back with its span preserved rather than returning nothing —
   silent emptiness invites fabrication.
4. Clamping is applied inside the data layer, below every tool, so a new tool added
   later inherits it by construction.

---

## 6. Historical Replay Engine

For any historical date T:

```text
What data was available?
What features were computable?
What targets existed?
What model was active?
What prediction would have been produced?
What happened afterward?
How calibrated was it?
```

Historical replay is also the mechanism for generating early resolved learning data before years of live observations accumulate.

**Replay output is development evidence, not forecast evidence.** See 6A.2.

---

## 6A. Historical Universe Policy and Replay Integrity

Replay is now central to generating learning data. That makes two controls
load-bearing rather than optional. Both were present in earlier revisions and are
restored here because replay without them produces good-looking numbers instead of
errors.

## 6A.1 Survivorship and the historical universe

The 30-company focus cohort is **not** the historical test universe.

The historical universe is constructed point-in-time and must include companies that
later:

- delisted
- were acquired or merged away
- were suspended from trading
- moved out of the index or the liquidity band
- failed

For any historical date T, universe membership is reconstructed as it stood at T, using
only information knowable at T. A universe assembled from today's listed companies is
survivor-biased by construction: every historical study run on it will overstate
returns, understate drawdowns, and produce calibration that looks better than the
system deserves.

Requirements:

1. Universe membership is a versioned, point-in-time table, not a query against
   currently-listed names.
2. Delisting, suspension and merger events are first-class corporate actions with
   effective dates.
3. Every replay run records the universe version it used.
4. A replay run against a universe that cannot demonstrate delisted members for the
   period is rejected by the harness, not warned about.

## 6A.2 Replay-origin vs live-origin evidence

Replay-generated outcomes are backtest results. If the model, feature set or target
definitions were chosen with any knowledge of the replay window, calibration measured
on replay is in-sample. The entire DSR, PBO and holdout apparatus exists to prevent
this, and an unmarked replay stream routes around all of it.

Therefore every prediction carries:

```text
origin: REPLAY | SHADOW_LIVE | PRODUCTION_LIVE
```

| Origin | What it is | Lookahead risk | May reject a candidate | May promote a candidate |
|---|---|---|---|---|
| `REPLAY` | Reconstructed historical prediction | High — model and features may have been chosen knowing the window | Yes | **No** |
| `SHADOW_LIVE` | Issued in real time on live data, not acted on | None — the future did not exist at issue | Yes | Yes |
| `PRODUCTION_LIVE` | Issued in real time and surfaced through the API | None | Yes | Yes |

`SHADOW_LIVE` is the workhorse evidence class. It carries no lookahead risk because
the outcome had not occurred when the claim was written, and it accumulates from the
day the agent starts running rather than from the day it is trusted.

And the following rules bind:

1. The three origins are **never pooled** in any calibration report, reliability
   diagram or effective-N computation. They are reported side by side with separate
   N_raw and N_effective.
2. Promotion gates requiring calibration evidence are satisfied by `SHADOW_LIVE` or
   `PRODUCTION_LIVE` claims only. `REPLAY` evidence may inform development and may
   reject a candidate, but may never promote one.
3. A replay run executed after the feature set or model was selected is tagged
   `replay_post_selection` and is excluded from every gate.
4. The Model Health Dashboard shows replay and live calibration as two separate
   series. Convergence between them is itself a diagnostic; divergence is an alert.

---

## 6B. Point-in-Time Applies to Learned Knowledge

Sections 5, 6 and 6A control what **data** a historical run may see. They say nothing
about what the system had **learned** by that date, and that is a second leakage
channel of equal severity.

A replay run dated in the past must not benefit from a calibration curve fitted on
outcomes that resolved after that date, a feature weight set derived from later
evidence, a decay demotion triggered later, a base rate updated later, or a
post-mortem lesson about an outcome that had not yet occurred. Any of these makes
replay evidence look better than the system was, and because replay is central to
generating early learning evidence (section 6), the error propagates into everything
downstream.

### 6B.1 Learned artifacts carry an effective date

Every learned artifact records when its evidence became known, not when it was
computed:

```text
artifact_id
artifact_type            # calibration_map | base_rate | feature_weight |
                         # decay_demotion | postmortem_lesson | selection_policy
knowledge_effective_from # the resolution date of the LATEST outcome it used
derived_from_claims[]
version
```

`knowledge_effective_from` is the resolution date of the latest outcome the artifact
was fitted on — the date the artifact *could first have existed* — not the date the
job ran.

### 6B.2 Replay filters on it

1. A replay run as of date T may load only artifacts with
   `knowledge_effective_from <= T`.
2. An artifact without a `knowledge_effective_from` is **excluded** from any replay
   query. Conservative exclusion, not best-effort inclusion: an artifact of unknown
   vintage is indistinguishable from a leaking one.
3. The artifact versions loaded are recorded on every replay prediction, so a replay
   result can be audited for what it knew.
4. A replay run that cannot resolve the artifact set for its date fails. It does not
   fall back to current artifacts.

### 6B.3 Lessons are point-in-time too

A post-mortem lesson (section 31A) is a learned artifact. Its
`knowledge_effective_from` is the resolution date of the claim it reflects on, not
the date the post-mortem was written. A lesson may not be injected into any run dated
before that.

---

## 7. Multi-Horizon Target Architecture

### Short horizon

Initial candidates:

```text
5D
10D
20D
30D
```

Purpose: technical signals, short-term momentum/reversal, volatility and event reactions.

### Intermediate horizon

```text
60D
90D
120D
```

Purpose: sector-relative performance, earnings trajectory, valuation, business momentum and catalysts.

### Long horizon

```text
6M
12M+
```

Purpose: strategic thesis, valuation convergence, structural growth, quality and capital allocation.

Targets are versioned in the human-owned Methodology Registry.

---

## 8. Multi-Horizon Feature Architecture

Features are evaluated as:

```text
Feature × Target × Horizon × Regime × Universe
```

A feature may be useful for one target and useless for another.

The architecture therefore does not label an indicator globally as “good” or “bad.”

---

## 9. Stage 3.5 Feature Tiers

### Tier A — Admitted initially

Naturally compatible with medium/long horizons:

- 3M relative strength
- 6M relative strength
- 12M relative strength
- sector-relative strength
- multi-horizon momentum
- distance from 52-week high
- realized volatility
- maximum drawdown

These are candidates, not automatically accepted factors.

### Tier B — Risk/state features

Examples:

- ATR
- realized volatility
- Bollinger width
- volume/average-volume ratio
- drawdown state

These may inform risk, uncertainty, position sizing and regime. They do not need to be direct return predictors.

### Tier C — Short-horizon features

Initially held from the 60–120D return-prediction search unless a justified target exists:

- RSI
- MACD
- MACD histogram
- Bollinger position
- OBV
- volume acceleration
- short moving-average crossovers
- short-term momentum

They become eligible when appropriate short-horizon targets exist.

This is a **search-budget and target-alignment rule**, not a claim that these features are inherently ineffective at longer horizons.

---

## 9A. Information-Domain Feature Families

Tiers A/B/C above govern price-derived features. Two further families enter with the
event and sentiment domains, and inherit tier semantics by horizon.

| Family | Examples | Typical horizon | Governing gate |
|---|---|---|---|
| Fundamental | Growth, margins, earnings quality, leverage, cash conversion, valuation | 90D – 12M | Standard admission |
| Event / news | Event type, novelty, materiality, event direction, surprise, event clustering | 5D – 120D+ | Tier C gate where horizon ≤ 30D |
| Sentiment | Level, change, attention, dispersion, crowding | 5D – 90D+ | Tier C gate where horizon ≤ 30D, plus 4B.2 restrictions |
| Regime | Macro, market and sector state | Routing only | Not a directional feature |

Regime features route and condition. They are never admitted as standalone
directional predictors.

---

## 10. Feature Registry

Every feature records:

```text
feature_id
feature_family
definition
formula
parameters
data_dependencies
economic_hypothesis
rationale_timestamp
target_compatibility
horizon_compatibility
regime_compatibility
cross_sectional_requirements
dependency_group
leakage_rules
minimum_effective_sample
status
version
created_by
```

Lifecycle:

```text
PROPOSED
→ PREREGISTERED
→ CANDIDATE
→ TESTING
→ SHADOW
→ PRODUCTION
→ DEGRADED
→ DEMOTED
→ RETIRED
```

Blocking states, enterable from any stage:

| State | Meaning | Exit |
|---|---|---|
| `HELD` | Progression paused pending an external condition — a data fix, a human decision, a dependency | Returns to the state it left, with the hold reason recorded |
| `REJECTED` | Failed a gate on evidence | Terminal for that Feature Card version. Re-entry requires a **new** card with a new preregistered rationale, and the rejection stays in search history for DSR |
| `DEMOTED` | Was in production, removed on decay or drift evidence (section 28) | May return to TESTING; its production history is retained |

`REJECTED` being terminal for the card version is what stops a failed candidate from
being quietly resubmitted until it passes. The rejection remains in the trial count
either way.

---

## 11. Economic Rationale Preregistration

Before evaluation, a Feature Card must contain:

- economic mechanism
- expected direction
- target
- horizon
- prior evidence
- falsification condition
- expected regime sensitivity

The pre-test rationale is immutable after evaluation begins.

Post-test interpretation is stored separately.

This prevents an LLM from inventing a theoretical explanation after seeing results.

---

## 12. Feature × Target × Horizon Matrix

Illustrative governance matrix:

| Feature | 10D | 20D | 90D | 6M | 12M | Risk/State |
|---|---:|---:|---:|---:|---:|---:|
| RSI | Candidate | Candidate | Hold | Hold | Hold | ✓ |
| MACD | Candidate | Candidate | Hold | Hold | Hold | |
| OBV | Candidate | Candidate | Hold | Hold | Hold | ✓ |
| 6M momentum | | | ✓ | ✓ | ✓ | |
| 12M momentum | | | ✓ | ✓ | ✓ | |
| 52W-high distance | | | ✓ | ✓ | ✓ | ✓ |
| ATR | ✓ | ✓ | ✓ | | | ✓ |
| Max drawdown | | | ✓ | ✓ | ✓ | ✓ |
| ROCE | | | ✓ | ✓ | ✓ | |
| FCF yield | | | ✓ | ✓ | ✓ | |

A check mark means “eligible to research,” not “proven predictive.”

---

## 13. Feature Testing Pipeline

```text
Idea
 ↓
Pre-registration
 ↓
Feature Card
 ↓
Data validation
 ↓
Leakage test
 ↓
Redundancy test
 ↓
Target/horizon compatibility
 ↓
Research experiment
 ↓
Validation stack
 ↓
Incremental contribution test
 ↓
Promotion decision
```

---

## 14. Cross-Sectional Feature Governance

The 30-company focus cohort is insufficient for general cross-sectional factor research.
Breadth requirements below apply to the **research universe** defined in section 3A,
never to the coverage cohort.

Initial admission rule:

```text
≥100 simultaneously eligible securities
```

plus, where applicable:

```text
≥20 distinct resolution cohorts
≥2 materially distinct market regimes
sufficient effective sample for the statistical test
```

Preferred mature research breadth:

```text
150–200+ securities
```

Breadth must also consider distinct companies, sectors, resolution dates and regimes.

---

## 14A. Benchmark Registry

Relative and excess-return targets are undefined without a benchmark that is itself
point-in-time. "Outperforms its sector peer set over 90 days" resolved against today's
peer set is resolved against information that did not exist when the claim was made.

Every benchmark is a registered, versioned artifact:

```text
benchmark_id
benchmark_name
type                      # index | sector | custom peer basket
constituent_source
constituent_history       # point-in-time membership with effective dates
weighting_method
rebalancing_rule
total_return_or_price
currency
version
effective_from / effective_to
```

Rules:

1. Claim resolution uses the benchmark version that was current **at claim issue**,
   not at resolution.
2. Peer baskets are constructed from point-in-time membership. A company that left the
   sector during the horizon is handled by a declared rule, not ad hoc.
3. Index reconstitution is a benchmark version change, recorded with its effective
   date.
4. Cross-sectional feature governance (section 14) anchors to a registered benchmark;
   an unregistered peer set cannot be used for admission evidence.
5. Total-return and price-return series are never mixed within a single evaluation.

---

## 15. Effective Sample Size

Every statistical report distinguishes:

```text
N_raw
N_effective
```

Company-date observations may be correlated through market, sector, macro and common resolution-date effects.

Use appropriate dependence-aware uncertainty methods, such as:

- cluster-robust standard errors
- two-way company × resolution-cohort clustering where supported
- block/bootstrap approaches
- other documented estimators

The method used must be recorded.

---

## 16. Calibration

Calibration is a primary system-health metric.

For probabilistic binary predictions:

```text
Primary: Brier Score
```

Additional diagnostics:

- reliability diagram
- calibration slope
- calibration intercept
- log loss
- expected calibration error where appropriate
- resolution
- uncertainty

The calibration set must be separate from the final untouched holdout.

---

## 17. Calibration Bin Policy

Initial reliability displays use:

```text
3–5 broad bins
```

Production interpretation requires:

```text
N_effective ≥ 50 per bin
```

Small bins can be monitored but cannot satisfy a promotion gate.

The 50-observation rule is a project governance threshold, not a universal statistical theorem.

---

## 18. Calibration Failure and Abstention

State machine:

```text
PROBABILISTIC
 ↓
WARNING
 ↓
FAILED
 ↓
ABSTAIN / QUALITATIVE
```

If calibration fails materially, unsupported probabilities must not continue to be presented as trustworthy.

The system may investigate recalibration and challengers, but probability output remains gated until the calibration contract is restored.

---

## 19. Intermediate Resolvable Claims

Every long-term thesis emits shorter resolvable claims.

Examples:

- next-quarter revenue direction
- margin direction
- guidance versus actual
- named catalyst fires by date
- invalidation condition
- sector-relative performance

These resolve in approximately 60–120 days where applicable and provide learning data long before a 12M thesis resolves.

---

## 20. Claim Dependency

Every claim records:

```text
parent_thesis_id
dependency_group_id
causal_role
```

The system distinguishes:

```text
forecast count
```

from:

```text
independent evidence
```

Correlated claims from one underlying catalyst are not treated as independent observations.

---

## 21. Prediction Ledger

Each prediction records:

```text
prediction_id
timestamp
data_snapshot_id
model_version
feature_set_version
target_id
horizon
prediction_distribution
bear/base/bull probabilities
expected value/distribution
confidence/calibration state
abstention state
rationale
parent thesis
dependency group
agent_messages[]            # see below — full inter-agent audit trail
evidence_snapshot_id        # immutable reference to the evidence state at issue
evidence_selection_version  # which selection policy applied (30A.1)
supporting_evidence[]
contradictory_evidence[]    # empty is a defect, not a strong thesis (30A.2)
missing_evidence[]          # feeds abstention and coverage discovery
origin                      # REPLAY | SHADOW_LIVE | PRODUCTION_LIVE  (see 6A.2)
universe_version            # point-in-time universe used
benchmark_version           # see 14A
replay_post_selection       # bool; excludes the claim from all gates
```

Point estimates alone are insufficient.

Every inter-agent message in the run is logged, not only the final output:

```text
message_id
run_id
from_agent / to_agent
model_id and model_version
prompt_version
latency_ms
fact_ids_injected[]
numeric_verification_result     # 30B.1
citation_verification_result    # 30B.2
degradation_flags[]             # 4E
```

Without this, a wrong memo cannot be attributed to a stage. Error attribution (31A)
distinguishing `extraction` from `reasoning` requires knowing what each agent was
handed and what it returned — which is only available if it was recorded at the time.

A claim with `origin: REPLAY` may never satisfy a promotion gate. A claim with no
`universe_version` is not resolvable and is rejected at write time.

---

## 22. Feature Promotion Effective-N Gate

A feature cannot enter production merely because a backtest metric looks attractive.

Promotion requires:

```text
minimum effective observations
minimum distinct companies
minimum distinct periods
regime coverage
robustness
incremental contribution
multiple-testing adjustment
```

A provisional general cross-sectional starting point is:

```text
N_effective ≥ 200 company-date observations
≥50 distinct companies
≥20 resolution cohorts
≥2 materially distinct regimes
```

These are governance starting points and can be tightened through the Methodology Registry.

The effective-N requirement for a feature is test-specific; it is not automatically identical to the 50-per-calibration-bin rule.

---

## 22A. Economic Evaluation and Transaction Costs

Economic evaluation converts a prediction into an estimate of value. That estimate is
wrong by exactly the amount of cost it fails to model.

Policy by horizon:

| Horizon band | Cost treatment |
|---|---|
| 6M and 12M targets | Costs immaterial to the research conclusion; may be omitted, but the omission is stated in the report |
| 90D targets | Explicit round-trip cost assumption required (brokerage, STT, exchange charges, stamp duty, GST) |
| Tier C short-horizon targets (10D, 20D) | Full cost model required — round-trip costs **and** a slippage/impact assumption — before any economic claim or promotion |
| Event and sentiment features at horizons ≤ 30D | Same as Tier C. The gate attaches to the **horizon**, not to the feature family — a feature cannot escape it by arriving through a different domain |

Rules:

1. No Tier C feature is promoted on an economic evaluation that omits costs.
2. The cost model is a versioned artifact under the Methodology Registry, not a
   constant embedded in evaluation code.
3. Every economic figure in any report states which cost model version produced it.
4. Where costs are omitted by policy, the report says so explicitly rather than
   silently presenting a gross figure.

This platform does not execute. Cost modelling exists to stop short-horizon features
looking valuable when they are not.

---

## 23. Experiment Harness

All economic evaluations pass through one harness.

Automatically record:

```text
experiment_id
research_family
candidate
dataset_version
feature_versions
target
horizon
parameters
timestamp
result
status
```

No supported production research workflow may bypass the harness.

---

## 24. Automatic Trial Counting

The experiment counter increments at the evaluation boundary.

Record:

```text
attempted
completed
failed
rejected
selected
```

Any candidate reaching quantitative/economic evaluation enters the search history.

LLM reasoning that never reaches evaluation is not a backtest trial.

---

## 25. Multiple Testing and Search Governance

Required controls include:

- purged cross-validation
- embargo
- CPCV / CSCV-style robustness
- walk-forward testing
- untouched holdout
- shadow deployment
- Deflated Sharpe Ratio
- Probability of Backtest Overfitting

DSR/PBO calculations use the relevant search-family trial history.

Hyperparameter restrictions alone are not considered sufficient control.

---

## 25A. Search-Space Expansion Control

Adding an information domain multiplies the candidate feature space. Deflated Sharpe
prices that expansion by discounting a result for the number of configurations tried
to find it — which means domain additions and DSR are a matched pair. Removing one
while adding the other is the most dangerous single change that can be made to this
architecture, and it is the change most likely to happen by accident during a
document revision.

Rules:

1. Admitting a new information domain (a new class of input, not a new feature within
   an existing class) is an architecture change request. It states the expected
   candidate count it introduces.
2. Each domain receives its **own experiment family** with its own declared budget and
   its own validation allocation. Domains do not share a budget, and a domain cannot
   borrow unused budget from another.
3. The DSR trial count for any candidate includes the full search history of its
   domain family, not the trials for that candidate alone.
4. No domain may be admitted while the multiple-testing controls in section 25 are
   disabled, incomplete or unvalidated on real data.

---

## 26. Validation Stack

```text
Data leakage checks
 ↓
Purged / embargoed CV
 ↓
CPCV / combinatorial robustness
 ↓
Walk-forward chronological testing
 ↓
Untouched holdout
 ↓
Shadow deployment
 ↓
Production promotion
```

CPCV and walk-forward answer different questions. CPCV evaluates robustness across recombined blocks; walk-forward evaluates chronological deployment behavior.

---

## 27. Holdout Lifecycle

```text
Current holdout
 ↓
Protected
 ↓
Promotion evaluation
 ↓
Retired
 ↓
Archived
 ↓
New untouched holdout
```

The final holdout is never a routine tuning set.

Calibration data must be disjoint from the final promotion holdout.

---

## 28. Feature Decay Monitor

Every production feature receives rolling monitoring for:

```text
rolling IC / Rank IC
incremental contribution
proper-score contribution
feature exposure
relationship/correlation drift
regime-specific contribution
```

State:

```text
HEALTHY
WARNING
DEGRADED
DEMOTED
```

Automatic demotion requires sustained degradation and adequate evidence. A single poor window does not automatically retire a feature.

---

## 29. Regime Engine

Identify conditions such as:

- bull/bear
- high/low volatility
- high/low dispersion
- liquidity conditions
- sector leadership
- macro stress

Regime information can condition feature usefulness, model selection, risk, confidence and abstention.

Regime conditioning must not become a mechanism for unrestricted data mining.

---

## 30. Model Architecture

Use horizon-aware models rather than forcing every target into one model:

```text
Short-horizon model
Intermediate-horizon model
Long-horizon model
        ↓
Integrated thesis engine
```

The distinction between horizons is preserved.

---

## 30A. Adaptive Evidence Selection and Contradictory Evidence

Not all evidence is decision-relevant for every security, regime, horizon or context.
A bank and a cement producer are not read with the same evidence set; a 20-day claim
and a 12-month thesis are not read with the same one either.

### 30A.1 Selection

Evidence relevance is selected by security characteristics (sector, size, liquidity,
business model), regime state, target horizon, and data availability. Selection is
**declared and recorded per prediction**, never implicit.

Constraints:

1. Selection chooses which evidence is *examined*, never which conclusion is reached.
2. The selection rule is versioned. Two predictions made under different selection
   rules are not directly comparable and are tagged accordingly.
3. Selection is auditable: the ledger records what was selected **and what was
   deliberately excluded, with the reason**.
4. Selection is not an agent decision made freshly each run. It is a registered policy
   that an agent applies.

### 30A.2 Contradictory evidence is mandatory

A thesis supported only by confirming evidence has not been tested. Every prediction
must carry three evidence sets:

| Set | Definition |
|---|---|
| Supporting | Evidence consistent with the claim |
| Contradictory | Evidence inconsistent with the claim, found and retained |
| Missing | Evidence that would be decision-relevant and could not be obtained |

Rules:

1. An empty contradictory set is a **defect**, not a strong thesis. It is flagged for
   review, because on any real security something disagrees.
2. Contradictory evidence is never removed during synthesis. It may be weighed and
   argued against; it may not be dropped.
3. The missing set feeds two places: abstention (section 34), and Coverage Discovery —
   a dimension that is repeatedly missing is a candidate for schema expansion.
4. Sentiment disagreeing with fundamentals or events is recorded as conflict evidence,
   not reconciled away (4B.1).

---

## 30B. Role-Declared Grounding Precedes the Critic

Section 31A's critic is a model, and a model can miss. The checks below need no model
at all, and running them first means the critic spends its attention on reasoning
rather than on arithmetic it is poorly suited to police.

These are gates, not advisories. Output that fails them does not reach the critic.

### 30B.1 The figure declaration block

A bare membership test cannot work, because not every legitimate number is in the
fact set. A price target is not an observation. A citation needs a source check, not
a value check. A count of items in a list is derived from the text itself. Testing
all of them against the fact set produces false rejections on correct output and
false passes on fabrications — and inferring which is which from the surrounding
prose fails for the reason recorded above.

So the model **declares** what each number is, in a structured block alongside its
output, and deterministic code validates each declaration against the evidence
ledger.

Five roles, and nothing else is valid:

| Role | Meaning | Validation |
|---|---|---|
| `observed` | A value read directly from evidence | Must match a fact in the injected set, within the band in 30B.3 |
| `derived` | Computed from observed values | The computation is re-executed deterministically from the cited inputs and must reproduce the value |
| `proposed` | A target, scenario or forecast the system is asserting | Must **not** be presented as observed; must carry the claim that owns it and appear in the ledger as a prediction |
| `cited` | A figure attributed to a named external source | The source must be in the retrieved set (30B.4); the value is not checked against our facts |
| `count` | A count of items in the output or evidence | Recomputed from the artifact it counts |

Rules:

1. Every measurement-shaped number in the output must carry a declaration. An
   undeclared measurement is a failure — the absence of a declaration is itself the
   finding, so there is no phrasing that slips through.
2. A declaration whose role fails its validation is a failure, even when the value
   appears somewhere in the fact set. A `proposed` number matching an observed fact
   is still a mislabelled forecast.
3. Validation reads **no natural-language word**. Role comes from the model; shape
   comes from the parser (30B.2). The gate has no vocabulary to become stale.
4. Per-role failure rates are monitored per agent and per model, and feed the
   diversity policy in 35A.

### 30B.2 Shape classification and normalisation

Numbers are classified by **shape**, not by meaning, and shape is
language-independent. This matters directly for Indian filings, which mix scripts,
use lakh and crore, and group digits as 1,23,456 rather than 123,456. A parser built
on Western grouping mis-tokenises Indian financial text; a parser built on English
keywords fails on the rest of it.

Shapes recognised, and only these:

```text
date / time / year      structure, never a measurement
symbol / identifier     digits inside an identifier (SMA20) are not numbers
list marker / ordinal   a line-leading "1." numbers the line, not the world
table row index         a cell that only numbers its row
measurement             everything else that is a quantity — the only shape that
                        requires a declaration
bare integer            context-dependent; declared or excluded explicitly
```

Before any matching, text is normalised: invisible and zero-width characters,
Markdown escapes, HTML character references, look-alike digits and separators. Every
offset is mapped back to the original text so a finding points at what the reader
sees. Without this, a homoglyph digit or a zero-width space silently defeats the gate.

Indian conventions are handled as declared numeral systems, not special cases: lakh
and crore multipliers and Indian digit grouping are registered forms, and a number
written in one is normalised to a canonical value before comparison.

### 30B.3 Tolerance is directional

`observed` and `derived` values match within a relative band of **0.005**.

The band may only be **narrowed** by written precision, never widened. Rounding
0.82467 to 0.82 exceeds the band, and the correct response is for the answer to
retain more digits — not for the gate to accept a coarser figure. A system that
widens its tolerance to accommodate rounding has stopped verifying.

Unit conversion and scale changes (crore to million, basis points to percent) are
declared transformations applied deterministically before comparison, never inferred.

### 30B.4 Citation and reference verification

Fabricated but plausible citations are among the most common failure modes in agents
that read retrieved content.

1. Every URL, document reference and filing citation must appear in the **retrieved
   result set** for that run.
2. References not in the retrieved set are **removed**, and the removal is recorded
   as an evidence gap under 4E — not silently dropped.
3. A claim whose only support was a removed reference becomes unsupported and is
   deleted by the critic.
4. A `cited` figure whose source was removed fails with its source.
5. Fabrication rates per agent and per model are monitored alongside the per-role
   failure rates in 30B.1.

### 30B.5 Ordering

```text
generate → shape scan + normalisation → declaration completeness
         → per-role validation → citation verification → identity check (30C)
         → provenance resolution → release decision (30D)
         → critic → output contract
```

The critic never runs on output that has failed a deterministic gate. Its job is
reasoning and adversarial challenge, not arithmetic.

---

## 30C. Identity Is Locked at the Agent Loop

Section 4 resolves identity at ingestion. That does not prevent the failure where a
correct number is attached to the wrong company — which passes every value check,
because the value is real.

1. A figure may not be attached to an instrument that **no tool call in this run**
   passed in or returned. Attribution to an entity the run never touched is a
   grounding failure, not a reasoning error.
2. The identity in force is **locked before the current tool-call batch begins**. An
   agent cannot resolve a new identity mid-batch and attribute earlier results to it.
3. An answer that contradicts the resolver about an entity's nature — asserting a
   listed company is private, or relabelling a locked identity — is an **identity
   finding**, reported separately from figure findings. The two have different fixes.
4. Identity findings are attributed to the `data` or `extraction` classes in 31A, not
   to `reasoning`.

---

## 30D. Graduated Release

A binary reject-and-regenerate loop has two failure modes: it discards output that is
almost entirely sound because of one bad figure, and it can consume the whole run on
a number that was never going to resolve.

### 30D.1 Revision budget

```text
rejection 1  → correction prompt naming the specific findings
rejection 2  → release with the rejected figures REDACTED
beyond       → REVIEW (34.1)
```

Two revisions maximum. The second release carries the redaction as a structured
evidence gap (4E), so a reader sees that something was cut and what kind of thing it
was.

### 30D.2 What may be redacted

Only findings where removing the figure leaves the rest of the output sound: an
unmatched value, an undeclared measurement, a figure attached to an unsourced symbol,
an unavailable claim. A finding that invalidates the thesis rather than one sentence
is **not** redactable and goes to `REVIEW`.

Redaction removes the figure and the sentence that depends on it. It never replaces a
number with a vaguer one — "roughly", "approximately", "around" applied to a figure
that failed verification is a fabrication with a hedge attached.

### 30D.3 Recovery is budgeted separately

An agent may make bounded, read-only tool calls to ground a figure that failed — up
to six rounds — and that budget is **separate from the revision budget**, so
grounding recovery never starves genuine research. Recovery calls are read-only and
cannot widen scope or invoke a tool outside the agent's declared set (35A).

---

## 30E. What Is Mechanically Decidable, and What Is Not

Three revisions of this document have converted prose rules into mechanisms. That
conversion has a boundary, and stating it prevents two opposite errors: leaving an
enforceable rule as advice, and building a brittle checker for something that cannot
be decided by a machine.

**Structural — enforced by a gate, output rejected on failure:**

- identity used and attributed (30C)
- every measurement declared, and each declaration valid for its role (30B.1)
- values within the directional band (30B.3)
- citations present in the retrieved set (30B.4)
- nulls carrying a missing-data class (4C)
- `origin` and `universe_version` present on every claim (21)
- schema conformance of extraction output (4D.1)

**Advisory — stated in the system prompt, judged by the critic, never gated:**

- stating the as-of date in prose
- research framing rather than advice
- refusing out loud rather than producing a hedged non-answer
- the quality of an argument
- whether the contradictory evidence set is genuinely adversarial rather than
  token (30A.2 makes an empty set a defect; it cannot make a weak one one)

A rule moves from advisory to structural only when someone demonstrates a
deterministic test for it. A rule is never moved the other way to make a failing gate
pass.

---

## 31. Self-Learning Research Loop

```text
Observe
 ↓
Predict
 ↓
Resolve outcome
 ↓
Score
 ↓
Diagnose error
 ↓
Generate research hypothesis
 ↓
Prereigster hypothesis
 ↓
Run controlled experiment
 ↓
Validate
 ↓
Champion / Challenger
 ↓
Human approval
 ↓
Promotion
```

Learning does not mean unrestricted optimization.

---

## 31A. Error Attribution Platform

When a forecast resolves badly, the default response must not be to retrain
everything. Untargeted retraining consumes holdout and search budget for what is often
a data fault.

Every resolved claim that fails materially enters attribution, which classifies the
failure into exactly one primary and any number of contributing categories:

| Class | Question it answers | Owner of the fix |
|---|---|---|
| `data` | Was an input wrong, stale, misclassified or revised? | Data Trust Platform |
| `extraction` | Was the filing parsed or mapped incorrectly? | Extraction agent + parsers |
| `feature` | Was the feature computed correctly but uninformative at this horizon? | Feature Registry |
| `model` | Were inputs correct and the mapping to probability wrong? | Quant Engine |
| `calibration` | Was the direction right and the confidence wrong? | Calibration Engine |
| `regime` | Did the relationship hold historically but not in this state? | Regime Engine |
| `reasoning` | Did the analyst agent draw an unsupported inference? | Research agents |
| `benchmark` | Was the target or comparison mis-specified? | Benchmark Registry |
| `target` | Was the target itself badly defined — wrong window, wrong resolution rule, unmeasurable as written? | Target Registry |
| `event_surprise` | Was the information state read correctly and then invalidated by genuinely new information? | No fix; recorded |
| `cost_execution` | Was the direction right and the economics wrong once costs and impact were applied? | Economic Evaluation (22A) |
| `irreducible` | Correct process, correct target, unfavourable outcome within the stated probability | No fix; recorded |
| `unknown` | Attribution attempted and failed | Triage queue |

Rules:

1. `irreducible` must be available and must be used. A system that attributes every
   loss to a fixable cause will chase noise indefinitely.
1a. `irreducible` and `unknown` are **not interchangeable**. Irreducible means the
   process was sound and the outcome fell in the tail — expected at a stated rate, and
   a well-calibrated system produces them constantly. Unknown means attribution was
   attempted and failed, which is a defect in the attribution process itself. Collapsing
   them hides the second behind the first. A rising `unknown` rate is an alert; a stable
   `irreducible` rate consistent with stated probabilities is health.
1b. `event_surprise` is not a reasoning error. A correct read of the information state
   available at issue, invalidated by information that did not then exist, is the system
   working. Recording it as `reasoning` would train the research agents away from
   correct behaviour.
1c. `cost_execution` separates prediction quality from economic quality. A claim that
   was directionally right and economically negative is a costing failure, not a
   forecasting failure, and the fix belongs to the cost model.
2. Attribution is recorded before any remediation is proposed.
3. Aggregate attribution over a window drives where effort goes. If 60% of failures
   are `data`, no amount of model work helps.
4. Attribution counts feed the research planner's priority queue; they do not
   automatically trigger changes.

---

## 32. Research Labs

Separate research families:

```text
Feature Lab
Factor Lab
Model Lab
Coverage Lab
Data Quality Lab
Calibration Lab
```

Each has explicit experiment budgets.

No lab can modify:

```text
scoring definitions
calibration targets
promotion thresholds
validation rules
holdout policy
```

---

## 33. Champion / Challenger

Production:

```text
CHAMPION
```

Alternatives:

```text
CHALLENGERS
```

Challengers run in shadow until they pass the promotion process.

No silent promotion.

---

## 34. Abstention Engine

Abstention is a first-class production component.

Trigger examples:

- calibration failure
- inadequate effective sample
- materially stale data
- critical source conflict
- leakage failure
- robustness failure
- insufficient evidence
- excessive uncertainty
- severe feature/model drift

Output can be:

```text
NO PROBABILISTIC FORECAST
```

with qualitative research output where appropriate.

### 34.1 ABSTAIN and REVIEW are different outcomes

`ABSTAIN` is a decision: the system examined the evidence and concluded it cannot
support a calibrated view. It is a correct, intended output and a sign of health.

`REVIEW` is a defect: the system produced output that could not be parsed, validated
or mapped to the decision vocabulary. Nothing was decided.

Collapsing the second into the first — or worse, into HOLD — is a specific and
damaging failure. A decision nobody can read is not a neutral position, and a neutral
position recorded in its place is quoted back to later runs as a call that was never
made, contaminating both the ledger and any lesson derived from it.

Rules:

1. Unparseable or unmappable output becomes `REVIEW`. It never degrades to `HOLD`,
   `ABSTAIN` or any tradeable or neutral state.
2. `REVIEW` is not a prediction. It does not enter the ledger as a claim, is excluded
   from calibration and effective-N, and triggers a re-run or human inspection.
3. `REVIEW` rate is monitored as a system-health metric, alongside the `unknown`
   attribution rate and the `extraction_failure` rate. All three measure the same
   thing: the system failing to know what it did.
4. The decision vocabulary is defined in **one place** and imported by every producer
   and consumer. Vocabularies restated at each call site drift, and drift between
   producer and consumer is how a valid decision becomes unparseable.

---

## 35. Scoring Governance

Human-owned artifacts:

```text
scoring function
calibration target
acceptance criteria
promotion thresholds
risk thresholds
abstention thresholds
```

These are version-controlled methodology artifacts.

No self-learning loop can rewrite them.

---

## 35A. Agent Inventory — What Is an Agent and What Is a Service

Most of this platform is deterministic services, not agents. The distinction is
load-bearing: an agent is a component where an LLM exercises judgement and can
therefore emit unverifiable text. Every agent is a place where errors enter that code
cannot catch, so the count is kept deliberately small and each one has a narrow,
declared scope.

### Deterministic services — not agents

Ingestion, reconciliation, fact store, corporate actions, feature calculator, leakage
tests, redundancy screens, quant models, calibration engine, outcome resolution,
historical replay, validation harness, experiment harness, trial counter, abstention
engine, scoring. These are jobs and libraries. None of them calls an LLM.

The abstention engine in particular is **rule-driven, not an agent**. It must be
predictable.

### V1 agents — four

| # | Agent | Scope | Output verified by |
|---|---|---|---|
| A1 | Extraction | Filings, results, transcripts → structured candidate facts | Deterministic validators + reconciliation against a second source |
| A2 | Analyst | Three declared roles: business/moat, guidance delta, risk & red flags | Critic + provenance check |
| A3 | Critic | Adversarial verification; every quantitative claim traced to a fact record | Deterministic provenance resolver |
| A4 | Synthesis | Assembles the memo and the structured claim set from verified inputs | Output contract validation |

A2 is one service with three prompts, not three deployments.

### V2 agents — three more, added only with the learning platform

| # | Agent | Scope |
|---|---|---|
| A5 | Post-mortem | Proposes error attribution class and the what-would-have-changed-this analysis |
| A6 | Feature proposal | Generates feature candidates with pre-registered economic rationale |
| A7 | Research planner | Prioritises the experiment queue within the declared budget |

### Deferred

A8 Methodology lab — proposes changes to the research method itself. Not built until
the learning loop has a full cycle of live-origin evidence behind it.

### Naming discipline

A data adapter is a **Service**, not an Agent, however it is labelled in a build plan.
The distinction is not cosmetic: it tells a reviewer where to look for errors that
code cannot catch. Market data, fundamentals, corporate filings ingestion, the feature
factory and the target engine are Services. They are deterministic, testable against
fixtures, and contain no LLM.

Where a build plan uses "Agent N" as a sequencing label, the agent inventory above
remains authoritative on which of those components may call a model.

### Shadow-first construction

Specialist components are **not** built to completion before the research agent
exists. One real end-to-end Equity Research Agent is built early and runs in
`SHADOW_LIVE` from the first day it produces anything, with specialists thickened
underneath it over time.

The reasons:

1. A vertical slice surfaces integration failures in weeks that a bottom-up build
   hides for months.
2. `SHADOW_LIVE` evidence accumulates from the day the agent starts running, not from
   the day it is trusted. Given the effective-N floors in sections 15 and 22, starting
   the clock early is worth more than starting it correct.
3. Shadow output is free of consequence, so an immature agent costs nothing but
   compute.

Shadow operation is subject to one hard rule: **no production action originates from
shadow mode**, and shadow claims are tagged at write time, never reclassified
afterward.

### Orchestration

Orchestration is a **fixed graph**, not an autonomous planner. A7 prioritises what
enters the queue; it does not decide which pipeline stages run. No agent may add,
skip or reorder a stage.

### Model diversity on adversarial pairs

Two agents running the same model share the same priors, the same training
distribution and the same blind spots. A bull and bear pair on one model is not a
debate — both cases are drawn from one distribution, and the disagreement is stylistic
rather than substantive. The same applies to an analyst and the critic reviewing it.

1. **A3 (critic) must not run the same model as A2 (analyst).** A model is a weak
   reviewer of its own reasoning patterns.
2. **The bull and bear roles must run different models**, ideally from different
   providers with different training corpora.
3. Model assignment per role is **declared, versioned, and recorded on every
   prediction**. It is not chosen at runtime by availability.
4. Where a fallback model is configured, the fallback is recorded on the claim and
   the claim is tagged as a degraded run under 4E. Model substitution is a variance
   source, not an implementation detail.
5. Diversity is a correlated-failure control, not a quality control. It does not
   license using a weaker model in a synthesis seat.

### Least privilege

Each agent receives the minimum tool set and the minimum credentials for its declared
scope. Capability is granted per agent, never per environment.

| Agent | Tools | Credentials |
|---|---|---|
| A1 Extraction | Document read only | None beyond its model key |
| A2 Analyst | Fact-store read only | Model key only |
| A3 Critic | Fact-store read only | Model key only |
| A4 Synthesis | None | Model key only |
| A5 Post-mortem | Ledger read only | Model key only |
| A6 Feature proposal | Registry read, propose-only write | Model key only |
| A7 Research planner | Queue read/write within budget | Model key only |

Rules:

1. No agent receives the process environment. Each is passed the one credential it
   needs, explicitly.
2. No agent has terminal, filesystem write, or network access beyond its declared
   tools.
3. No agent holds a write credential to the fact store, the scorer, the objective
   spec or the holdout.
4. A web-searching component, if added, runs with search only and no other capability,
   and its output passes through 30B.2 before use.

### Ceiling

```text
V1:       4 agents
V1 + V2:  7 agents
Ever:     8 agents
```

Any proposal to add a ninth is an architecture change request requiring a stated reason
why the work cannot be done deterministically.

---

## 36. API Layer

Conceptual request:

```json
{
  "symbol": "TICKER",
  "analysis_type": "full",
  "horizons": ["10D", "90D", "12M"]
}
```

Response:

```text
Data quality
Fundamental analysis
Technical/state analysis
Valuation
Risk
Regime
Short-horizon forecast
Intermediate thesis
12M thesis
Bear/Base/Bull distribution
Calibration state
Confidence state
Abstention status
Evidence/provenance
```

Internal research complexity remains behind the API.

---

### 36.1 The query surface cannot trigger tool calls

Any interactive query endpoint — asking a question about an existing analysis —
answers **only from that run's stored notes and ledger entries**. It cannot invoke an
agent, a tool, a web search, or a fresh model call against external content.

1. Queries are served from stored artifacts. No path from the query surface reaches a
   tool.
2. A question the stored artifacts cannot answer returns that fact. It does not
   trigger new research.
3. The query surface never produces a new prediction and never writes to the ledger.
4. It is rate-limited and returns research output, not advice.

This closes the obvious injection route: a query surface that can trigger a tool call
lets an outside input drive the system's behaviour, which is exactly what 4D.1 rule 3
forbids internally.

---

## 37. Output Contract

Full analysis should contain:

1. Data quality
2. Business overview
3. Financial health
4. Growth
5. Profitability
6. Cash flow
7. Balance sheet
8. Valuation
9. Market/technical state
10. Sector comparison
11. Regime
12. Catalysts
13. Risks
14. Intermediate claims
15. 12M thesis
16. Bear/Base/Bull distribution
17. Calibration status
18. Confidence state
19. Abstention state
20. Evidence/provenance

---

## 38. Technology Strategy

Recommended stack:

```text
Python
PostgreSQL / DuckDB
Parquet
Pandas / Polars
NumPy
scikit-learn
LightGBM / XGBoost where justified
QLib for quantitative research infrastructure
MLflow or equivalent experiment tracking
FastAPI
Docker
Git/GitHub
Codex for implementation
RD-Agent later for controlled research automation
```

The architecture must remain modular and not depend on a single framework.

---

## 39. Repository Structure

```text
ai-equity-agent/
├── apps/api/
├── config/
├── data/
│   ├── raw/
│   ├── validated/
│   ├── point_in_time/
│   └── snapshots/
├── src/
│   ├── ingestion/
│   ├── data_quality/
│   ├── provenance/
│   ├── universe/
│   ├── features/
│   ├── targets/
│   ├── models/
│   ├── calibration/
│   ├── validation/
│   ├── experiments/
│   ├── ledger/
│   ├── regimes/
│   ├── abstention/
│   └── research/
├── tests/
├── notebooks/
├── docs/
├── configs/
└── README.md
```

---

## 40. Development Sequence

Each numbered item below is complete only when its stated acceptance test passes.
Phase boundaries are hard: no item from a later phase begins until every item in the
current phase has a green test. Acceptance tests for the load-bearing items are given
in 40A.

### Phase A — Foundation
1. Git repository
2. Python environment
3. configuration
4. logging
5. database/data lake
6. source registry
7. provider abstraction

### Phase B — Data Trust
8. ingestion
9. normalization
10. quality checks
11. provenance
12. point-in-time snapshots
13. corporate actions
14. historical replay foundation

### Phase C — Feature Platform
15. Feature Registry
16. Feature Cards
17. preregistration
18. horizon/target mapping
19. feature calculator
20. leakage tests
21. redundancy tests

### Phase D — Stage 3.5
22. Tier A features
23. Tier B risk/state features
24. short-horizon targets
25. Tier C technical features
26. feature evaluation

### Phase E — Validation
27. purging/embargo
28. CPCV
29. walk-forward
30. holdout
31. DSR
32. PBO
33. calibration
34. effective-N diagnostics

### Phase F — Learning
35. prediction ledger
36. intermediate claims
37. outcome resolution
38. error attribution
39. feature decay
40. champion/challenger
41. research labs

### Phase G — API
42. analysis orchestration
43. output contract
44. FastAPI
45. monitoring

---

## 40A. Acceptance Tests for Load-Bearing Items

The items below fail silently if wrong. Each needs a test written before the next
phase starts.

| Item | Acceptance test |
|---|---|
| 5 database | Schema migrates from empty and rolls back cleanly |
| 7 provider abstraction | Provider swapped behind the interface; no downstream file changes |
| 11 provenance | Every stored fact resolves to a raw artifact hash |
| 12 point-in-time | Write a fact, correct it a week later, query as of a prior knowledge date, get the original value |
| 13 corporate actions | A known split produces a continuous adjusted series and a discontinuous raw series |
| 14 replay foundation | Replay at date T cannot access any artifact whose knowledge time exceeds T |
| — universe (6A.1) | Replay over a period containing a delisting includes the delisted name |
| 17 preregistration | A feature evaluated before its rationale is registered is rejected by the harness |
| 20 leakage tests | A deliberately leaked feature is caught and rejected |
| 24 automatic trial counting | An evaluation run outside the harness is impossible, not merely discouraged |
| 30 holdout | A second read of a retired holdout is refused |
| 35 ledger | A claim without `universe_version` or `origin` is rejected at write time |
| 37 outcome resolution | Resolution uses the benchmark version current at claim issue |

---

## 40B. Implementation Sequence From the Current Codebase

Section 40 gives the phase model. This is the concrete ordered sequence from where the
code actually stands, with a definition of done for each step. A step is complete when
its test passes, not when it runs.

| # | Build item | Done when |
|---|---|---|
| 1 | Freeze v1.6 | Changes are applied as diffs; no full rewrites |
| 2 | Data Source Registry | Every source declares authority, schema, frequency, timestamp semantics and reliability |
| 3 | Data Trust Engine | A deliberately corrupted input is quarantined, not ingested |
| 4 | Point-in-Time + Provenance | Write a fact, correct it a week later, query as of a prior knowledge date, get the original value |
| 5 | Historical Universe / Survivorship | Replay over a period containing a delisting includes the delisted name |
| 6 | NSE Market Data Adapter | Provider swapped behind the interface with no downstream file change; a known split produces a continuous adjusted and discontinuous raw series |
| 7 | Fundamental Data Adapter | Consolidated and standalone never mix; basis is explicit on every fact |
| 8 | Corporate Event Adapter | Syndicated republication of one release collapses to one event |
| 9 | News / External Adapter | Extraction confidence is stored separately from investment confidence |
| 10 | Sentiment Adapter | Features below the liquidity threshold are refused, not down-weighted (4B.2) |
| 11 | Knowledge / Event Hub | All domains normalise to one point-in-time evidence object |
| 12 | Real Feature Factory | A feature evaluated before its rationale is registered is rejected (section 11) |
| 13 | Real Target Engine | Resolution uses the benchmark version current at claim issue (14A) |
| 14 | Equity Research Agent v0.1 | Produces a claim set with every quantitative claim traced to a fact record |
| 15 | Prediction Ledger | A claim without `origin` or `universe_version` is rejected at write time |
| 16 | Shadow operation | No production action can originate from shadow; origin is set at write time |
| 17 | Outcome Resolver | Intermediate 60–120D claims resolve without manual intervention |
| 18 | Error Attribution | Every materially failed claim carries a class, including `irreducible` (31A) |
| 19 | Calibration + Abstention | Gates read `SHADOW_LIVE` evidence only; bins meet the effective-N floor (17, 22) |
| 20 | Decay / Drift | A decayed feature is demoted automatically (section 28) |
| 21 | Controlled Self-Learning | Every experiment consumes declared budget; running outside the harness is impossible (24) |
| 22 | Specialist agents | Added while v0.1 keeps running; agent count stays within the ceiling (35A) |
| 23 | API + Orchestrator | Every response carries provenance, model version and origin |

Steps 1–13 are Services. Only step 14 introduces an agent.

---

## 40C. Component Status Register

This register is the authoritative statement of what exists. It is updated as a diff,
and a component moves to "integrated" only when its 40B test passes on real data.

| Component | State | Next action |
|---|---|---|
| Feature Card / Registry | Prototype | Integrate with real data; enforce preregistration rejection |
| Target Registry / Engine | Prototype | Connect real targets and point-in-time benchmark definitions |
| Research dataset / panel | Prototype on synthetic | Replace synthetic panels with trusted real data |
| Effective-N / statistics | Prototype | **Revalidate on real dependency structures** — synthetic panels have clean dependence; real ones do not |
| Purged / CPCV / WFA / holdout | Prototype | Align purge windows to actual target horizons |
| Multiple testing / experiment ledger | Prototype | Connect to automatic family tracking per domain (25A) |
| Economic evaluation | Prototype | Add cost and impact model before any ≤30D promotion |
| Lifecycle / promotion | Prototype | Bind to human approval and real evidence |
| Shadow evaluation | Prototype | Merge into the authoritative ledger with `origin` |
| Real ingestion / Data Trust | Not built | Immediate priority |
| News / events / sentiment | Not built | Second priority |
| Equity Research Agent | Not built | Build in parallel with data foundation |
| Calibration / attribution / learning | Not built | After shadow predictions accumulate |

**Standing risk:** the entire statistical layer was built and tested against synthetic
panels. It is unvalidated against real dependency structure. Treat every effective-N
and purging result as provisional until step 4 of 40B is green and the statistics have
been re-run on real data.

---

## 40D. Architectural Rules Are Enforced by Static Tests

Several rules in this document are stated as prose and would be violated silently:
evaluation code must not be importable from research notebooks (24), vendor access
belongs only in the data layer, the run date must not appear in a model-visible
schema (5A.2), no null may be written without a class (4C).

A rule that depends on a reviewer noticing is not enforced. Each becomes a test that
parses the source tree and fails on commit.

| Rule | Static test |
|---|---|
| Vendor access is confined to the data layer | Parse every module's imports; assert vendor libraries appear only under the data layer |
| Evaluation runs only inside the harness | Assert the evaluation entry point is imported by nothing outside the harness package |
| The run date is not model-visible | Assert no tool schema exposed to an agent declares a date parameter that state also injects |
| Features declare a preregistered rationale | Assert every Feature Card in the registry has a rationale timestamped before its first evaluation record |
| Nulls carry a class | Assert no write path constructs a fact with a null value and no missing-data class |
| Decision vocabulary is single-sourced | Assert the rating and decision enums are defined once and imported, not restated |
| Agents hold only declared credentials | Assert no agent construction path reads the process environment for secrets |
| Critic and analyst differ | Assert the configured model ids for the adversarial pairs are not equal |
| Verification precedes the critic | Assert the critic entry point is unreachable except from the verification stage |
| Grounding reads no prose vocabulary | Assert the grounding package contains no natural-language keyword list and imports no provider or tool registry |
| Roles are closed | Assert the role enum has exactly the five members and is defined once |

Rules for this section:

1. These tests run in CI on every commit, not on a schedule.
2. A test here is never marked expected-to-fail to unblock work. The rule is either
   enforced or removed from the architecture.
3. When a leak or violation is found in operation, the fix includes a static test
   that would have caught it. A fix without a test is not complete — this is how a
   leakage class stops recurring.

---

## 41. Minimum Viable Vertical Slice

Do not implement all modules before proving the end-to-end pipeline.

Initial slice:

```text
30 companies
1 exchange
historical market data
core fundamentals
Tier A features
one 90D target
one short-horizon target
basic calibration
prediction ledger
historical replay
validation harness
API
```

Then thicken the layers that fail or prove most valuable.

---

## 41A. What Counts as Learning — and What Does Not

With research labs generating candidates automatically, activity becomes abundant and
meaningless. The negative definition is the more important half.

### This counts as learning

1. Out-of-sample calibration improves on live-origin claims at adequate effective N.
2. A feature is promoted after surviving the full validation stack with its search
   cost accounted.
3. A feature is **demoted** on decay evidence.
4. Error attribution shifts measurably — the same failure class stops recurring after
   a targeted fix.
5. A hypothesis is rejected on evidence, and the rejection is recorded so it is not
   re-proposed.
6. Coverage expands: a new dimension enters the schema after appearing in several
   independent post-mortems.
7. Abstention rate falls without calibration degrading, or rises appropriately when
   evidence weakens.

### This does not count as learning

1. Number of experiments run.
2. Number of features in the registry.
3. Number of memos produced.
4. Backtest performance improving.
5. In-sample or replay-origin calibration improving.
6. The model changing.
7. A larger model, a newer model, or more context.
8. Any metric that improves while live-origin calibration is flat.

Rule 8 is the test that subsumes the rest. If live-origin calibration is flat, nothing
has been learned regardless of what else moved, and the correct response is to
investigate why rather than to ship the thing that moved.

---

## 42. Codex Usage

Codex is primarily an implementation and engineering assistant.

Human-owned:

- hypotheses
- methodology
- scoring
- calibration acceptance
- promotion thresholds
- holdout policy
- interpretation

Recommended workflow:

```text
Architecture contract
 ↓
Codex implementation task
 ↓
Automated tests
 ↓
Human review
 ↓
Merge
```

---

## 43. RD-Agent Integration

RD-Agent is a later-stage research automation component.

It may propose:

- new features
- feature transformations
- factor combinations
- model variants
- research hypotheses

Every candidate enters:

```text
Preregristration
 ↓
Experiment Harness
 ↓
Automatic Trial Count
 ↓
Validation
 ↓
Promotion Gate
```

RD-Agent is a research generator, not the authority on its own research validity.

---

## 44. Statistical Methodology Reference Set

Maintain durable references for:

- Bailey & López de Prado — Deflated Sharpe Ratio
- Bailey, Borwein, López de Prado & Zhu — Probability of Backtest Overfitting / CSCV
- López de Prado — Advances in Financial Machine Learning, including purging and embargo concepts
- Brier-score / Murphy decomposition literature for probabilistic calibration
- Proper-scoring and calibration methodology

These references provide methodological foundations; project thresholds remain human-owned and versioned.

---

## 45. Architecture Decision Log

Every major decision records:

```text
decision_id
date
problem
options
decision
reason
impact
supersedes
owner
```

This preserves why decisions were made and prevents silent architectural drift.

---

## 46. Change Management

The baseline is frozen for implementation, but not immutable forever.

Changes require:

```text
Architecture Change Request
 ↓
Impact assessment
 ↓
Decision
 ↓
Version increment
 ↓
Migration plan
```

A justified change is allowed when evidence warrants it.

---

## 46A. Summary Documents Are Generated, Never Edited

A short executive summary of this architecture is useful and should exist. It is also
the mechanism by which sixteen controls were lost across three revisions.

Rule:

1. This document is the single baseline. Any summary is **generated from it** and
   carries the baseline version it was generated from.
2. A summary is never edited independently and never becomes the source for the next
   revision. An improvement noticed while writing a summary is applied here first, as
   a diff, and the summary is regenerated.
3. A summary that cannot state which baseline version produced it is void.
4. Every revision runs a **control audit** before adoption, across all four layers:
   data (entity resolution, missing-data classes, trust chain order, provenance),
   statistical (DSR, PBO, CPCV, purging, effective-N, bin policy, trial counting),
   governance (preregistration, budgets, holdout lifecycle, champion/challenger,
   scorer ownership), and evidence (contradictory set, abstention, error classes).
   Auditing one layer and assuming the others held is how ACR-32 and ACR-33 went
   missing for four revisions.

The failure mode this prevents is specific and has already occurred twice: a rewrite
optimises for readability, the prose that reads as excessive detail is exactly the set
of enforcement mechanisms, and the resulting document is more pleasant to read and
missing its controls. Drift always favours the summary, because the summary is the one
people want to read.

---

## 47. Acceptance Criteria

Production readiness requires:

1. Data provenance.
2. Point-in-time reconstruction.
3. Leakage tests.
4. Historical replay.
5. Automatic trial counting.
6. Enforced search budgets.
7. DSR where applicable.
8. PBO/CSCV where applicable.
9. Disjoint calibration data.
10. Protected final holdout.
11. Brier score for applicable probabilistic binary predictions.
12. Reliability diagnostics.
13. N_raw and N_effective reporting.
14. Calibration bins meeting minimum effective-N policy.
15. 60–120D intermediate claims where applicable.
16. Claim dependencies.
17. Feature decay monitoring.
18. Abstention.
19. Human-owned scoring and acceptance criteria.
20. Auditable champion/challenger promotion.
21. API provenance and model/version metadata.
22. Point-in-time survivorship-aware historical universe, including delisted members.
23. Replay-origin and live-origin evidence separated; gates satisfied by live-origin only.
24. Registered, versioned benchmarks with point-in-time constituents.
25. Error attribution recorded on every materially failed claim, including an irreducible class.
26. Cost model applied to every Tier C economic evaluation.
27. Agent count within the declared ceiling, each with a narrow declared scope.
28. Research and coverage universes separated, with every statistic declaring its universe.
29. Error attribution distinguishes `irreducible` from `unknown`, and tracks the `unknown` rate as an alert.
30. `REJECTED` is terminal for a Feature Card version and remains in the trial count.
31. Entity resolution keys on ISIN; ambiguous identifiers raise rather than resolve.
32. Every null carries a missing-data class; unclassified nulls are rejected at write time.
33. Every prediction carries supporting, contradictory and missing evidence sets.
34. Evidence selection policy is versioned and recorded per prediction, including exclusions.
35. Learned artifacts carry `knowledge_effective_from`; replay filters on it and excludes undated artifacts.
36. Vintage-less vendor fields are withheld from historical runs by one shared data-layer rule.
37. The run date is injected from state and absent from every model-visible tool schema.
38. Empty vendor responses are never cached; exhaustion emits one explicit no-data sentinel.
39. `REVIEW` never degrades to `HOLD` or `ABSTAIN` and never enters the ledger as a claim.
40. Each prose architectural rule in 40D has a passing static test in CI.
41. Every emitted numeral resolves to an injected fact or a declared derived form; unmatched numerals reject the output.
42. Every citation and URL appears in the retrieved result set; unmatched references are removed and recorded as gaps.
43. Retrieved content is wrapped as data; instructions found in sources are reported, never followed.
44. Critic and analyst run different models; bull and bear run different models.
45. Each agent holds only its declared tools and its single model credential.
46. Every degraded run carries a structured evidence gap in both output and ledger.
47. The query surface cannot invoke a tool or write to the ledger.
48. Every measurement-shaped number carries a role declaration; undeclared measurements reject the output.
49. Each declaration is validated per role; a mislabelled role fails even when the value exists in the fact set.
50. The grounding gate contains no natural-language vocabulary and is language-independent.
51. Tolerance may be narrowed by written precision and never widened.
52. No figure is attributed to an instrument the run never resolved.
53. Redaction never replaces a failed figure with a hedged approximation.

---

## 47A. Non-Negotiable Guardrails

Consolidated from the controls above. Each restates an obligation specified elsewhere;
none replaces its specification.

1. No future information in a past decision.
2. No silent rewriting of history — restatements append, never overwrite.
3. No survivor-only historical replay.
4. No benchmark ambiguity — resolution uses the version current at claim issue.
5. No pooling of `REPLAY` with live-origin evidence for any gate.
6. No manual trial-count understatement — counting is enforced in the harness.
7. No promotion on returns alone.
8. No gross short-horizon economics without cost and impact analysis.
9. No confidence number without calibration evidence at adequate effective N.
10. No automatic global retraining after a single failure — attribute first.
11. No self-modification of ground truth, scoring, acceptance thresholds or promotion policy.
12. No production action originating from shadow mode.
13. No treating activity metrics as learning.
14. No admitting an information domain while multiple-testing controls are incomplete.
15. No sentiment feature as decisive evidence in a claim.
16. Contradictory evidence and the ability to abstain are always preserved.

---

## 48. v1.4 Frozen Baseline

v1.4 establishes the implementation baseline for a multi-horizon, self-learning equity research platform.

The key commitments are:

```text
Point-in-time data
+
Multi-horizon targets
+
Feature preregistration
+
Feature-horizon matching
+
Effective sample size
+
Calibration as a primary metric
+
Controlled experimentation
+
Automatic trial counting
+
DSR/PBO
+
CPCV + walk-forward
+
Protected holdout
+
Intermediate resolvable claims
+
Feature decay monitoring
+
Abstention
+
Human-owned scoring
```

The system evolves through controlled research rather than uncontrolled self-modification.

---

## 49. Immediate Next Step

Before adding individual indicators, implement:

```text
Feature Registry
 ↓
Feature Card
 ↓
Preregristration
 ↓
Target/Horizon compatibility
 ↓
Feature calculation interface
 ↓
Evaluation Harness
```

Only then populate Stage 3.5 features.

**Do not begin autonomous feature optimization yet. Do not connect RD-Agent yet. Do not build a large predictive model yet.**

First make the research infrastructure capable of recording, evaluating and rejecting features correctly.

## 49A. Definition of Success

The system is successful when, for a real security, it can:

reconstruct the information state that was actually available at a specified past
time; verify, clean and entity-resolve that information; classify what is missing and
why; incorporate market, fundamental, event, news, sentiment and macro evidence;
select which evidence is decision-relevant for that security, regime and horizon;
retain the evidence that contradicts its own conclusion; produce an auditable
BUY / HOLD / SELL / ABSTAIN with a calibrated probability and a stated invalidation
condition; record the claim with its origin; resolve the outcome when it matures;
attribute the error when it is wrong; and convert validated findings into controlled
new experiments without contaminating the evaluation process.

Note what is absent from that statement. It does not mention returns, accuracy, or
outperformance. A system that does all of the above and discovers it has no edge has
succeeded — it has produced a reliable answer to a real question. A system that
produces good returns without the above has learned nothing and cannot be trusted to
continue.

---

## Current implementation position (v1.8)

Per the status register in 40C, the research and statistical layer exists in
prototype against synthetic data, and the data foundation does not exist yet. This
inverts the naive build order: the statistics are ahead of the data.

The next implementation work is **40B steps 2 through 6** — source registry, data
trust engine, point-in-time and provenance, survivorship-aware universe, and the real
NSE market data adapter. Step 4's test is the one that matters most and the one most
easily declared done prematurely.

Build steps 2–6 for the **research universe** (100+ names, prices and corporate
actions and benchmark membership only), not just the 30-company cohort. The depth
work in steps 7–11 stays scoped to the cohort. This is what unblocks revalidating the
statistical layer on real dependency structures, which is the largest unquantified
risk in the project and is currently gated on breadth, not depth.

In parallel, and deliberately not after: begin the Equity Research Agent v0.1 (step
14) as soon as steps 6 and 12 can feed it, and put it into `SHADOW_LIVE` immediately.
Shadow evidence accumulates from the day it runs, and the effective-N floors in
sections 15 and 22 mean that clock is the binding constraint on everything downstream.

Do not connect RD-Agent, do not begin autonomous feature optimisation, and do not
promote any feature until the statistical layer has been re-validated on real
dependency structures.
