# AI Self-Learning Equity Research & Market Analysis Agent
## Master Architecture v2.2.0 — Frozen Institutional Baseline

**Status: FROZEN.** This document supersedes every prior revision in both lineages and
is the single controlling architecture. It is amended only on a factual correction, a
security or compliance requirement, an evidence-driven defect discovered during
implementation, or a human-owned methodology decision that changes an authoritative
contract. Implementation inconvenience is never grounds for amendment.

v2.2.0 is an owner-approved amendment (section 46) made during implementation of the
repository `ai-equity-agent`, recorded there as ADR-007. It adds the global and India
macro context the Indian market depends on, cross-market timing, macro and geopolitical
event types, return-magnitude forecasts with a decision rule, a data-acquisition and
network policy, and a factual correction about which codebase sections 40C and 49
describe. It is applied as additions to v2.1.1: apart from the version line and the
'frozen at' line in 46A, every line of v2.1.1 is retained unchanged and in order (control
audit, 46A rule 4).

### Changes in v2.2.0

| # | Change | Section |
|---|---|---|
| ACR-103 | Global and India macro context made explicit inside the Sector/macro domain: rates and bonds, currencies, commodities, world equity markets, volatility, credit stress, economic releases, investor flows, monsoon and policy calendar | 3B rule 4, new 3G |
| ACR-104 | Cross-market timing: every series carries its market session, time zone and publication time; a foreign close enters an Indian decision only after it exists | new 5C |
| ACR-105 | Macro, policy and geopolitical event types registered; an event without an issuer reaches a security only through a declared route | 4A.0, 4A rule 5 |
| ACR-106 | Macro exposure features (measured company sensitivity applied to an observed factor move) are company features under standard admission; raw macro state stays routing-only | 9A, 9C |
| ACR-107 | Regime engine gains global dimensions | 29 |
| ACR-108 | Implementation sequence: steps 6a (price-history acquisition), 9a (macro context), 9b (macro and geopolitical events) and 9c (aggregate investor flows) come before the Knowledge/Event Hub; 3F updated | 40B, 3F |
| ACR-109 | Data acquisition and network policy: terms checked per source, official and free sources first, paid sources only on owner approval, one network module with an allow-list, secrets never in chat, code or logs | new 4G |
| ACR-110 | Return-magnitude forecasts: per registered horizon, probability of gain and of outperformance and a calibrated range of absolute and benchmark-relative return, scored by proper scoring rules; a preregistered decision rule maps them to BUY / HOLD / SELL / ABSTAIN | new 7A, 16, 18, 21, 36, 37 |
| ACR-111 | Purpose and use: research for the owner's own decisions, never distributed as advice | 3 |
| ACR-112 | Factual correction: 40C and "Current implementation position (v2.1.1)" describe the predecessor codebase at checkpoint 49d639bb; this repository's position is recorded in its acceptance records (ADR-002) | 40C, closing position note |
| ACR-113 | Acceptance criteria 90-104 and guardrails 17-20 added for the above | 47, 47A |

Impact assessment (46): no existing control is removed or weakened. The added steps
before step 11 delay the start of the effective-N clock (3F); the owner accepted that
cost because a recommendation that ignores global conditions would rest on incomplete
evidence, and each added step is built to a current-decision baseline first to keep the
delay small. The macro-sensitivity candidates belong to the existing Sector/macro family
and count toward its DSR trial history (25A). No agent is added (35A ceiling unchanged).

v2.1.1 makes surgical corrections to v2.1. It introduces no new design.

### Corrections in v2.1.1

| # | Correction | Section |
|---|---|---|
| ACR-93 | Stale implementation-status rows removed — they contradicted the accepted record | 40C |
| ACR-94 | Stale pre-Step-12 next-step block replaced | 49 |
| ACR-95 | Bottom-20% demoted from primary exclusion to robustness screen; India-specific investability policy is primary | 14.0, 25A.1 |
| ACR-96 | Post-hoc risk-model shopping prohibited; factor lineage fields required | 22B |
| ACR-97 | Factor series is subject to point-in-time discipline like any other source | 22B |
| ACR-98 | Baseline outperformance is a gate for economic-alpha claims, not for every feature | 22C |
| ACR-99 | Cohort multiple-testing refined — routine forecasts are observations, not trials | 25A.2 |
| ACR-100 | Cost/capacity required for every economic promotion; keyed to turnover, not horizon | 22A |
| ACR-101 | Deterministic economic resolution attempted before UNRESOLVABLE | 21.1 |
| ACR-102 | Expanded domains declared non-blocking for the Step 13/14 critical path | new 3F |

Two of these (ACR-93, ACR-94) are defects introduced by patching, not design
disagreements. A future session following the stale §49 literally would have rebuilt
Steps 2 through 6.

v2.0 was rigorous about engineering and silent about asset pricing. It could establish
that a feature predicts returns, that the prediction is calibrated, that costs are
modelled and that the search was deflated — and never ask whether the returns were
simply exposure to known factors. v2.1 closes that gap and the ones around it.

### Change log from v2.0

| # | Change | Section |
|---|---|---|
| ACR-84 | Risk adjustment: promotion requires factor-model alpha, not raw return | new 22B |
| ACR-85 | Significance hurdle stated: t > 3.0, with size screen | 25A |
| ACR-86 | Standing baseline comparators the system must beat | new 22C |
| ACR-87 | Investability floor on the research universe | 14 |
| ACR-88 | `UNRESOLVABLE` terminal state for claims that cannot settle | 21 |
| ACR-89 | Cohort selection rule must be preregistered and dated | 3A |
| ACR-90 | Universe-level multiple testing from repeated analysis | 25A |
| ACR-91 | Signal combination defaults to equal weighting | new 22D |
| ACR-92 | Prior-literature library; published factors enter with a decay prior | 28, new 3E |

v2.0 merges two lineages that were developed in parallel:

- **Implementation lineage** (Architect v1.5 → v1.6, accepted through Stage 12X). Built
  against real NSE data. Authoritative for Steps 1–12.
- **Specification lineage** (v1.0 → v1.12). Reasoned from failure modes and external
  review. Authoritative for Steps 13–23, which the implementation has not reached.

Where the two disagree about the data layer, **the implementation lineage wins without
argument**. It was tested; this document was not. Where the specification lineage covers
ground the implementation has not reached, it stands until evidence replaces it.

Implementation baseline: source checkpoint `49d639bb2f174aa35f0a63746d3de88a3ff0ab3b`,
Step 12 `ACCEPTED_CURRENT_DECISION_BASELINE`, Step 13A next.

### Change log from v1.12

| # | Change | Section |
|---|---|---|
| ACR-69 | Current-decision PIT vs historical-replay PIT formally separated | 5B |
| ACR-70 | ELIGIBLE / NOT_ELIGIBLE / REVIEW availability disposition | 5B |
| ACR-71 | `REVIEW` name collision resolved | 5B, 34.1 |
| ACR-72 | Capability status vocabulary formalised | new 2A |
| ACR-73 | Corporate-action capability table and security-window fail-closed | new 6C |
| ACR-74 | Event-specific identity bridge; ISIN is not permanently stable | 4, new 6D |
| ACR-75 | Attention eligibility separated from sentiment eligibility | 4B |
| ACR-76 | Methodology preregistration extended beyond feature rationale | 11 |
| ACR-77 | Negative-assertion acceptance tests | 40D |
| ACR-78 | Tooling errors never trigger production mutation | new 40E |
| ACR-79 | Dependency-impact audit and binding-layer migration protocol | new 40F |
| ACR-80 | Spine-before-downstream build constraint | new 40G |
| ACR-81 | Acquisition boundary separated from methodology | 40G |
| ACR-82 | Capability-specific stage acceptance replaces binary phase gates | 40B |
| ACR-83 | Implementation position recorded against the real checkpoint | 40C |

v1.11 named seven information domains and nine event types and specified almost
nothing beneath them. This revision fills in the factor and event inventory, adds
sector-specific fundamentals, and defines how chart patterns may enter.

### Change log from v1.11

| # | Change | Section |
|---|---|---|
| ACR-60 | Ownership and flows as an information domain | 3B, new 3C |
| ACR-61 | Derivatives positioning as an information domain | 3B, new 3D |
| ACR-62 | Capital structure, credit, legal, index and governance event types | 4A |
| ACR-63 | Sector-specific KPI registry — fundamentals are not one flat set | new 9B |
| ACR-64 | Expanded fundamental factor inventory | new 9C |
| ACR-65 | Disclosure-text and event-response factors | 9C |
| ACR-66 | Information-leakage detection, and the boundary on its use | new 4F |
| ACR-67 | Chart-pattern admission path — deterministic definition required | new 9D |
| ACR-68 | No vision-model chart reading | 9D |

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

**Purpose and use (v2.2.0, ACR-111).** The system produces research and recommendations
for the owner's own investment decisions. Its outputs are not distributed to others as
advice; doing so would require registration under the SEBI (Research Analysts)
Regulations, 2014, and is out of scope. Every recommendation is a calibrated forecast
with its uncertainty and may be ABSTAIN; none is a guarantee.

---

## 2A. Capability Status Vocabulary

Every stage, feature, contract and capability carries exactly one of these. They are not
synonyms and must not be used loosely.

| Status | Meaning |
|---|---|
| `CLOSED` | The stage's agreed acceptance boundary is satisfied |
| `ACCEPTED_<CAPABILITY>_BASELINE` | A named capability is proven; other modes of the same stage are explicitly not claimed |
| `PROTOTYPE` / `SCAFFOLD` | Code exists, may have passing tests, is not the accepted operating path |
| `HELD` | Implemented and registered, intentionally prevented from promotion pending evidence |
| `BLOCKED` / `FAIL_CLOSED` | The system refuses to proceed for the affected case rather than infer a result |
| `DEFERRED` | Real future capability, outside the current stage's closure boundary |
| `AVAILABILITY_REVIEW` | Point-in-time state is not sufficiently proven to be eligible |

Four distinctions this vocabulary exists to protect, in ascending order of strength:

```text
a component exists
< a unit test passes
< a real-data integration passes
< a research method is statistically validated
< a feature or agent is production-authorized
```

**Software execution success is not research validity.** A calculation can be correct
while its predictive usefulness remains entirely unproven. Registration is not
admission. Calculation is not validation. Validation is not promotion. A passing
acceptance test is not production authorization.

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
4. **Global context belongs to these domains (v2.2.0, ACR-103).** World equity markets,
   interest rates and bonds, currencies, commodities, volatility, credit stress,
   economic releases, central banks and geopolitics move Indian prices mainly through
   foreign investor flows, input costs, the rupee and risk appetite. They are ingested
   as context series (3G) and events (4A.0) - never as covered securities: other
   countries' stocks stay outside the coverage and research universes. This clarifies
   the existing Sector/macro and News/external domains; it is not a new domain.

Two domains added in v1.12 and detailed below: **Ownership & flows** (3C) and
**Derivatives positioning** (3D). Both are Core.

---

## 3C. Ownership and Flows

Who owns a security and how that is changing is a distinct information domain, not a
subset of market data. For Indian mid-caps, promoter pledge trajectory is among the
highest-signal public variables that exists, and none of this was previously in the
architecture.

| Factor | Source | Notes |
|---|---|---|
| Promoter shareholding, level and change | Quarterly shareholding pattern | Dilution, stake sales |
| Promoter pledge, level and change | Exchange disclosures | Encumbrance is a leading distress indicator |
| Insider transactions | SEBI PIT disclosures | Direction, size, seniority of the transacting party |
| FII / DII net flows | Exchange and depository data | Security and aggregate level |
| Mutual fund holdings, change | Monthly disclosures | Concentration and conviction |
| Bulk and block deals | Exchange feeds | Counterparty where disclosed |
| Institutional concentration | Shareholding pattern | Crowding and exit risk |
| Free float | Computed | Liquidity and manipulability |

Rules:

1. Shareholding data is quarterly and lagged. Its `available_to_market_at` is the
   filing date, never the quarter end — this is a point-in-time trap that will
   otherwise produce an obvious and false edge.
2. Pledge is tracked as a trajectory, not a level. The change and its direction carry
   most of the information.
3. Insider transaction features are computed from **disclosed** transactions only.
   See 4F for the boundary on undisclosed information.

---

## 3D. Derivatives Positioning

India's F&O market is large relative to cash volumes and its positioning data is
public. For any security in the F&O segment this is often where informed positioning
becomes visible first. Its complete absence from v1.11 was the largest India-specific
gap in the architecture.

| Factor | Notes |
|---|---|
| Open interest and change | By expiry; the level alone is not informative |
| Put-call ratio | Volume-based and OI-based are different signals |
| Futures basis | Premium or discount to spot, and its trend |
| Monthly rollover percentage and cost | Rollover behaviour near expiry |
| Implied volatility, level and skew | Where options are liquid enough |
| Options OI concentration by strike | Positioning clusters |

Rules:

1. Positioning features apply only to securities in the F&O segment. Segment
   membership is point-in-time — inclusion and exclusion are events.
2. Expiry effects are structural. Features are computed expiry-aware; a raw OI series
   across a rollover is meaningless.
3. Positioning is evidence about market state, not a directional predictor by
   assumption. It enters the matrix (12) like any other candidate.
4. Most positioning features are short-horizon and therefore inherit the Tier C cost
   gate (22A).

---

## 3G. Global and India Macro Context (v2.2.0, ACR-103)

The Indian market does not move on Indian information alone. A rise in US Treasury
yields pulls foreign money out of Indian equities; crude oil sets the margins of oil
marketers, paint makers, airlines and chemical producers; the rupee decides what an IT
exporter earns; a war, a sanction or an OPEC+ decision reprices whole sectors overnight;
the Bank of Japan's rate path can unwind the carry trade that funds risk across Asia.
Section 3B already makes Sector/macro a Core domain and says its variables are direct
evidence for specific companies (rule 1). This section names the factors.

| Group | Factors | Main route into Indian equities |
|---|---|---|
| Rates and bonds | US 2Y and 10Y Treasury yields, US policy rate, US yield curve; India 10Y G-sec, RBI repo rate and liquidity; Japan and euro-area policy rates | Foreign flows, cost of capital, bank and NBFC margins, valuations |
| Currencies | USD/INR, broad US dollar index, USD/CNY, USD/JPY | Exporter and importer margins, foreign investors' dollar returns |
| Commodities | Brent and WTI crude, natural gas, gold, copper, aluminium, steel inputs, key agricultural prices | Input costs and realisations by sector |
| World equity markets | US (S&P 500, Nasdaq), Japan (Nikkei 225), China and Hong Kong (Shanghai Composite, Hang Seng), emerging markets; GIFT Nifty | Overnight risk appetite; sector read-across, e.g. US technology to Indian IT |
| Volatility and credit stress | US VIX, India VIX, US high-yield credit spreads | Risk-on / risk-off state |
| Economic releases | India CPI, WPI, IIP, GDP, GST collections, PMI; US CPI, payrolls, GDP; China activity data | Rate expectations, demand by sector |
| Investor flows | Daily FPI/FII and DII net flows, aggregate | The main channel through which global events reach Indian prices |
| Seasonal and structural | Monsoon progress against normal, Union Budget, election calendar, index-provider reviews (MSCI, FTSE) | Rural demand, policy shifts, passive flows |

Rules:

1. **Every series is point-in-time evidence** (5, 5A, 5B, 5C). A market value carries the
   session and time zone in which it was set; an economic release carries its
   publication time and every vintage. A revised figure is a new vintage, never an
   overwrite, and a series without vintages is withheld from historical replay (5A.1).
2. **Context, not coverage.** Foreign indices, yields and prices are evidence about the
   environment of Indian securities. They are never covered securities, never targets,
   and never benchmarks for Indian claims (14A).
3. **Two routes only.** A macro series enters a decision either as regime state (29;
   routing only, 9A) or through a security's measured sensitivity to it (9C, ACR-106).
   A raw macro level or change is never a standalone directional predictor for a
   security.
4. **Sector membership routes macro evidence** (9B rule 1). Until a point-in-time sector
   classification is registered, macro evidence reaches a security only through its
   measured sensitivity.
5. **Expected candidate count (25A).** The macro-sensitivity family is bounded at
   registration - each factor above, a declared set of estimation windows, and the
   registered horizons - and the count is declared on the Sector/macro family budget
   before the first evaluation. Every candidate counts toward that family's DSR history.
6. **Sources follow 4G.** Official and free sources first - central banks, statistics
   offices, exchanges, FRED and its vintage archive ALFRED - and a paid vendor only when
   a free source is shown insufficient and the owner approves it.

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
5. **Cohort selection is preregistered and dated.** How the coverage cohort was chosen
   is written down before it is used, with the rule, the date and the data as of that
   date. Selecting by recent performance, by familiarity, or by any criterion computed
   from the period to be evaluated contaminates every downstream statistic, and no
   later control recovers from it. Acceptable rules are mechanical and stated in
   advance — index membership at a date, liquidity rank at a date, sector coverage
   targets. Cohort changes are events with their own dated rationale.
6. A feature admitted on research-universe evidence is not thereby validated for the
   coverage cohort if the cohort differs systematically from the research universe in
   size, liquidity or sector mix. That difference is measured and recorded, not
   assumed away.

---

## 3F. Critical Path and Non-Blocking Capability

This architecture specifies substantially more capability than the current
implementation requires. Without an explicit statement of what is on the critical path,
a future session may read an unimplemented section as a prerequisite and stall.

**On the critical path to the first accepted vertical slice (Steps 13–16):**

Target Engine contract, benchmark-version-at-claim resolution, corporate-action
semantics in target windows, the Equity Research Agent v0.1, role-declared grounding,
the Prediction Ledger with origin, and shadow operation.

**Explicitly non-blocking — valuable, scheduled after the vertical slice runs:**

| Capability | Section |
|---|---|
| Ownership and flows domain | 3C |
| Derivatives positioning domain | 3D |
| Sector KPI registry | 9B |
| Expanded fundamental factor inventory | 9C |
| Chart-pattern admission | 9D |
| Sentiment feature admission | 4B, deferred at Step 10 |
| Full point-in-time sector routing | deferred at Step 12 |
| Historical replay | deferred at Step 12 |
| Prior-literature library integration | 3E |

Rules:

1. A non-blocking capability is never a reason to delay Step 13, 14, 15 or 16.
2. Non-blocking capabilities are added **after** the vertical slice produces
   shadow predictions, not before, and each enters through the normal admission route.
3. A non-blocking section being unimplemented is not a defect and is not recorded as
   one.
4. Moving a capability onto the critical path is an architecture change request.

**v2.2.0 (ACR-108).** Aggregate investor flows (from 3C), the macro context (3G) and
macro and geopolitical events are moved before step 11 at a current-decision baseline,
and price-history acquisition (step 6a) is added. The rest of 3C, all of 3D, and the
other rows above remain non-blocking. The cost is a later start of the effective-N
clock; the owner accepted it because a recommendation that ignores global conditions
would rest on incomplete evidence.

The binding constraint on this project is the effective-N clock, which does not start
until shadow predictions begin accumulating. Anything that delays that start is more
expensive than it appears.

---

## 3E. Prior-Literature Signal Library

Most characteristics a feature lab will propose have already been tested, published and
in many cases replicated. Treating them as discoveries wastes trial budget and
overstates novelty.

A registered prior library records, for each known characteristic: its definition, the
original paper's reported t-statistic, the replication t-statistic where one exists, the
publication date, and the market it was established in.

The primary reference is the Chen and Zimmermann open-source cross-sectional asset
pricing dataset (`github.com/OpenSourceAP/CrossSection`, data at openassetpricing.com),
which reproduces several hundred published predictors and — unusually — compares each
reproduction's t-statistic against the original paper's result. Its signal
documentation file is the index.

Rules:

1. Before a candidate enters the admission pipeline, it is checked against the prior
   library. A match is declared on the Feature Card.
2. A matched candidate is a **prior**, not a discovery. It must justify itself against
   the published effect size, and it enters with the decay prior in 28.
3. A prior established in another market is a weaker prior for Indian equities, not a
   free pass. The market of establishment is recorded.
4. The library is versioned and its own provenance is tracked. Published datasets carry
   errors: the Chen–Zimmermann data was patched in October 2024 to fix a look-ahead bias
   in one signal, caught by an outside reader — an instance of exactly the leak class
   5B exists to prevent, inside a careful academic dataset.

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

## 4F. Information Leakage — Detection and Boundary

Abnormal price, volume or open-interest movement in the window before an announcement
is measurable, and it is legitimate research material. Acting on undisclosed
price-sensitive information is not. The two must be separated in the architecture,
not left to judgement at run time.

### 4F.1 Detection is a governance signal

Pre-announcement abnormal activity is computed for every registered event where the
data supports it: abnormal return, abnormal volume, abnormal OI change, and delivery
percentage shift over a declared pre-event window against the security's own
baseline.

It is admissible as:

- evidence about the quality of the company's information governance
- evidence about the quality of the market in that security
- a risk factor raising the required evidence threshold, and a trigger for abstention

It is **not** admissible as:

- a directional signal about the content of the pending announcement
- an input to any prediction whose resolution depends on that announcement

This is a hard boundary in the feature registry. Leakage features carry a flag that
excludes them from directional targets tied to the event they precede.

### 4F.2 Undisclosed information is out of scope

Trading on unpublished price-sensitive information is prohibited under the SEBI
(Prohibition of Insider Trading) Regulations 2015. The system is built so it cannot
drift toward it:

1. Insider transaction features use **disclosed** filings only (3C).
2. No source that purports to carry pre-announcement non-public information is
   registered. This is a source-registry exclusion, not a run-time judgement.
3. Private tip channels — messaging-group forwards, unattributed "sources say"
   material — are an **excluded source class**, not a down-weighted one. They are
   also the primary distribution mechanism for manufactured signals in Indian small
   and mid caps, so the exclusion is warranted on data-quality grounds independently
   of the legal one.

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

### 4A.0 Registered event types

| Group | Event types |
|---|---|
| Results and guidance | Results, guidance issue, guidance revision, pre-quarter update |
| Operations | Order win, capex announcement, capacity commissioning, plant shutdown, price revision |
| Corporate actions | Dividend, bonus, split, buyback, rights issue, QIP, preferential allotment, warrant conversion, demerger, delisting |
| M&A and structure | Acquisition, divestment, JV, restructuring, promoter stake change |
| Governance | Auditor change or resignation, qualified opinion, KMP departure, board change, related-party transaction, accounting policy change |
| Credit and distress | Rating action, outlook change, default, debt restructuring, NCLT admission, IBC proceeding |
| Legal and regulatory | SEBI order, tax dispute, litigation, environmental or pollution board action, licence or clearance change |
| Index and market structure | Index inclusion or exclusion, F&O segment change, ASM or GSM surveillance stage, circuit or ban period |
| Monetary policy and rates (v2.2.0) | Central bank decision (RBI, Fed, ECB, BoJ, PBoC), policy-rate change, liquidity measure, sovereign bond auction stress |
| Fiscal, trade and regulation (v2.2.0) | Union Budget, tax or GST change, tariff or trade action, export or import restriction, production-linked incentive, sector-wide regulation |
| Sovereign and macro data (v2.2.0) | Sovereign rating or outlook action (India, US, others), major data release (CPI, GDP, payrolls, PMI), with its surprise against consensus only where a licensed consensus exists |
| Geopolitics and shocks (v2.2.0) | Armed conflict onset, escalation or ceasefire; sanctions; OPEC+ decision; supply disruption (shipping route, pipeline, plant); natural disaster; monsoon deviation; pandemic measures; election result |
| Index-provider and flow events (v2.2.0) | MSCI or FTSE country inclusion or weight change; large foreign-investor outflow or inflow episode |

Rules:

1. Capital-structure events have computable mechanical effects (dilution, share count
   change, float change). Those are computed deterministically and are facts, not
   interpretations.
2. Governance events are red flags by default and enter the forensic feature set in
   9C, not only the news stream.
3. Index and market-structure events cause mechanical flows and constraints
   independent of fundamentals, and must be separable from fundamental event response
   at analysis time.
4. **Read-across:** an event for one entity may be evidence for a related entity —
   supplier to customer, peer guidance to sector. Read-across links are declared in
   the entity graph and the derived evidence is tagged as read-across, never as a
   direct observation about the target.
5. **Events without an issuer (v2.2.0, ACR-105).** Macro, policy and geopolitical events
   carry their country or region, not an issuer. They reach a security only through a
   declared read-across link (rule 4), its point-in-time sector membership (9B), or its
   measured sensitivity to the factor the event moves (9C), and the route is recorded
   with the evidence. Their effect is measured as an event-response target (rule 3 of
   the next list), never assumed.

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

### 4B.4 Attention eligibility and sentiment eligibility are different

A story retrieved by a query about a company is not necessarily evidence about that
company. In the accepted implementation, 27 deduplicated stories from one company
query yielded **6 direct sentiment-eligible** stories and 21 that were query-context
only — while all 27 remained **attention-eligible**.

Two separate dispositions per story:

| Disposition | Meaning | Feeds |
|---|---|---|
| Attention-eligible | The story appeared in connection with this security | Attention, volume, novelty features |
| Sentiment-eligible | The story is **direct evidence about this issuer** | Sentiment level, dispersion |

Rules:

1. Sentiment features are computed only over sentiment-eligible stories. Query-context
   stories never contribute polarity.
2. Attention features may use the wider set, and must declare which set they used.
3. Entity assignment must be proven, not inferred from the query that retrieved the
   story. Until proven, the record carries an explicit unassigned marker and is never
   attributed to an issuer.
4. A story with a generic headline may still be direct evidence when URL or source
   evidence establishes the entity relationship. Headline matching alone is neither
   necessary nor sufficient.
5. **Deduplicate before aggregating. One underlying story is one vote.** Syndication
   across domains otherwise multiplies a single event into false independent evidence.
6. Every entity-resolution false positive found in operation becomes a named
   regression test.

### 4B.5 Model polarity is not issuer impact

A text-polarity model scores language, not economic consequence. An adverse regulatory
or litigation headline can score strongly positive, and in the accepted implementation
one did.

The raw model output is **never flipped after inspection**. It is preserved and the
disagreement is recorded as an event-versus-text-polarity conflict in the quality
layer. Tuning a model output because the result looked wrong after seeing it is the
purest form of researcher degrees of freedom, and the prohibition is absolute.

Unavailable sentiment dimensions — change, velocity, attention, novelty, spam
likelihood, calibrated source quality — remain missing. They are never zero-filled, and
"no news" is never converted into neutral sentiment.

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

## 4G. Data Acquisition and Network Policy (v2.2.0, ACR-109)

How data is obtained is part of its provenance. A source used against its terms can be
withdrawn, blocked or contested, and everything built on it goes with it.

1. **Terms first.** Before a source is registered (section 4) its terms of use are read
   and the licence recorded: permitted use, storage, automated access, use in AI
   systems, attribution and redistribution. A source whose terms forbid this use is not
   registered. Every source decision is an architecture decision record.
2. **Official and free before paid.** Exchanges, regulators, statistics offices, central
   banks and open datasets are tried first. A paid source is proposed only when a free
   one is shown insufficient for a named requirement, with its price, limits and terms,
   and it is adopted only on the owner's approval.
3. **No scraping.** Where a website's terms forbid automated collection, people download
   files by hand. Automated access is used only where the provider's terms permit it.
4. **One network boundary.** A single module in the data layer may open network
   connections - only to addresses on its declared allow-list, never following
   redirects, within each provider's limits, backing off and stopping when a provider
   refuses. Static tests enforce the boundary (40D).
5. **Secrets stay on the owner's machine.** API keys and passwords never appear in chat,
   in the repository, in logs, in stored URLs or in error messages. They are supplied
   through the environment or an untracked local file, read only by the network module,
   and passed to nothing else. No agent receives them (35A).
6. **Every response is kept** byte for byte as a raw artifact before it is read; a
   refused, empty or malformed response is never stored as an absence of data (4C.1).
7. **Acquisition contracts are versioned** (40G.2): a change of endpoint, format or limit
   is fixed at the acquisition boundary, never by loosening validation.
8. **Excluded and display-only sources stay out** (4F.2) - including when a vendor relays
   their content. Display-only data (for example TradingView) is never ingested.

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

## 5B. Availability Disposition and the Two PIT Claims

This section supersedes any weaker statement of point-in-time elsewhere in this
document. It is implementation-derived and authoritative.

### 5B.1 Availability is a disposition, not a boolean

Core rule: `available_at <= decision_time`.

| Disposition | Meaning |
|---|---|
| `ELIGIBLE` | Evidence is **proven** available by the decision time |
| `NOT_ELIGIBLE` | Evidence is **proven** unavailable by the decision time |
| `AVAILABILITY_REVIEW` | True availability is not sufficiently proven |

The third state is the one systems omit, and omitting it is how availability gets
manufactured. An observation's business or trading date does **not** prove when the
information became available. Neither does a filesystem timestamp, an HTTP
`Last-Modified` header, or an assumed end-of-day release time. Where availability is
unknown, the disposition is `AVAILABILITY_REVIEW` and the evidence does not enter a
decision.

It is normal and correct for a domain to sit in `AVAILABILITY_REVIEW` indefinitely.
In the accepted Stage-11 integration, all market evidence remained in review while
fundamentals, events, news and sentiment were eligible. That asymmetry is honesty, not
an incomplete implementation.

### 5B.2 Two different PIT claims

**Current-decision use.** A historical archive downloaded and verified today may
support a decision made today, from the time of verified ingestion, provided the
feature claims only current availability.

**Historical replay.** The same archive may **not** be presented as historically
available at an earlier decision date merely because the observation is dated in the
past. Replay requires separately proven historical availability and retrieval
semantics.

Conflating these is the single most dangerous error available in this system, because
the resulting backtest looks excellent and means nothing. A stage may therefore be
accepted for current-decision use while historical replay remains explicitly false.

### 5B.3 Naming

`AVAILABILITY_REVIEW` (this section) and `OUTPUT_REVIEW` (34.1, unparseable agent
output) are unrelated states with unrelated causes. Earlier revisions of both lineages
used the bare token `REVIEW` for each. The bare token is prohibited.

---

## 5C. Cross-Market Timing (v2.2.0, ACR-104)

Markets close at different hours. The US session ends after midnight India time, so a
US close dated 3 October did not exist during the Indian session of 3 October. Using it
there is look-ahead that no date comparison catches, because both values carry the same
calendar date.

1. Every market series records its exchange, session calendar and time zone. A value's
   `available_at` is the time it was set (its session close, in its own time zone) or
   published, converted to UTC - never its calendar date.
2. Evidence enters a decision only if `available_at <= decision_time` (5B). During the
   Indian session this admits Asian, European and US closes of earlier sessions, and an
   intraday value only where its timestamp is proven.
3. An economic release carries its scheduled release time and the vintage released then.
   A release whose time cannot be proven is `AVAILABILITY_REVIEW` for historical replay.
4. Holidays differ by market. A missing foreign value on an Indian trading day is a
   classified absence (4C: `structurally_absent` when that market was closed), never a
   carried-forward value presented as fresh.
5. Lead-lag effects between markets are measured, never assumed, and enter only through
   features admitted under the normal route (10, 11).

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

## 6C. Corporate-Action Adjustment Capability

Raw exchange close prices are unusable for return features across structural actions,
and a generic vendor "adjusted close" imports an unknown methodology. The adjustment
policy is therefore a frozen, versioned, human-owned contract, and its implemented
scope is narrower than its stated intent.

Raw exchange close remains **immutable**. The derived series carries its own identity.

| Action | Policy intent | Implemented scope |
|---|---|---|
| Split / reverse split | Back-adjust on verified official ratio | SUPPORTED factor |
| Simple equity bonus | Back-adjust on verified ratio | SUPPORTED factor |
| Ordinary cash dividend | Price return: no adjustment | SUPPORTED no-op |
| Buyback | No adjustment by default | SUPPORTED no-op |
| Rights | Official factor, or deterministic TERP only with verified ratio, subscription price and ex-date | BLOCKED |
| Special dividend | Price-index-consistent treatment | BLOCKED |
| Merger / amalgamation | No automatic successor splice | BLOCKED |
| Demerger / spinoff | Authoritative reference-price treatment | BLOCKED |
| Complex or unparsed bonus | No approximation | BLOCKED |
| Unknown or conflicting terms | Quarantine | BLOCKED |

**No factor may ever be inferred from an observed price jump.** This is the temptation
when terms will not parse, and it silently fabricates history.

The gap between intent and implementation is the point of the table. A policy that
claims full coverage while the engine handles two action types is worse than one that
states both.

### 6C.1 Security-window fail-closed

```text
window_start < ex_date <= window_end
```

If this holds for an unsupported or unresolved action, block **that security's feature
window** — not the universe, and not the feature. Universe-wide blocking on one
unparsed action makes the system unusable and pushes implementers toward
approximation.

### 6C.2 Exchange feeds may not carry structured factors

Corporate-action feeds frequently encode terms in free text rather than structured
fields. A rights entry may read as a ratio and premium inside a subject line, which is
not equivalent to a structured subscription-price field. Only mechanically complete
forms generate factors; everything else fails closed.

---

## 6D. Identity Bridges — ISIN Is Not Permanently Stable

Section 4 makes ISIN the primary key, which is correct against symbol. It is not
sufficient: **ISIN itself changes**, and a security's corporate-action records may
carry an ISIN that its price series never uses.

Contract model: **event-specific, evidence-backed alias**.

Permitted only with all of:

- exact action symbol match
- normalised company-name continuity
- the expected source series
- exactly one market ISIN covering that event's ex-date

Prohibited absolutely:

- symbol-only bridges
- global ISIN equivalence
- rewriting raw identities
- discarding historical actions because the current ISIN differs

A bridge is scoped to **one corporate-action event**. It asserts nothing about any
other event, date or dataset, and every bridge decision is auditable. Where evidence is
insufficient, no bridge is created and the affected window fails closed under 6C.1.

Source-native identifiers are preserved in lineage throughout. Canonical identity
normalisation happens at the evidence boundary, not by rewriting the source.

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

## 7A. Return-Magnitude Forecasts and the Decision Rule (v2.2.0, ACR-110)

The owner's question is concrete: which stock to buy, hold or sell, and what gain to
expect from holding it for a stated number of days or months. Section 21 already
requires a prediction distribution and an expected value on every claim; this section
makes that output explicit, measurable and honest.

For each covered security and each registered horizon (7), a claim carries:

| Output | Meaning |
|---|---|
| P(gain) | Probability that the security's total return over the horizon is positive |
| P(outperform) | Probability of beating the registered benchmark (14A) over the horizon |
| Absolute return range | 10th, 25th, 50th, 75th and 90th percentiles of total return over the horizon, after the declared cost model (22A) |
| Excess return range | The same percentiles relative to the benchmark |
| Decision | BUY / HOLD / SELL / ABSTAIN under the registered decision rule |
| Invalidation condition | The observable event that would show the claim wrong before the horizon ends |

Rules:

1. **Horizons are registered targets.** "x days or months" is one of the registered
   horizons (5D to 12M+, section 7). A new horizon is a new registered target,
   preregistered before use (11).
2. **Ranges, never single numbers.** A gain is reported as a percentile range with the
   probabilities above. The median is labelled as a median, never as a target price.
3. **Magnitude forecasts are scored with proper scoring rules** - pinball (quantile) loss
   and the continuous ranked probability score - and calibrated by interval coverage:
   across many claims the 10-90 range must contain the outcome about 80% of the time.
   Brier scores (16) continue to score P(gain) and P(outperform). Both are reported side
   by side, by horizon and by origin (6A.2).
4. **Calibration gates magnitude separately.** If interval coverage fails materially,
   the return range is withheld under section 18 while a calibrated direction may still
   be shown; if direction also fails, the claim is ABSTAIN.
5. **The decision rule is a human-owned, versioned artifact (35)**, preregistered before
   any claim uses it (11). It maps the calibrated outputs to the decision vocabulary
   defined in one place (34.1 rule 4) - for example BUY only when P(outperform) and the
   lower part of the excess-return range both clear stated thresholds after costs. The
   owner sets the thresholds; no learning loop may change them.
6. **Risk adjustment applies (22B).** An expected excess return explained by known
   factor exposure is labelled as factor exposure, not as alpha.
7. **Improvement is measured, not assumed (41A).** The system gets better only if
   live-origin calibration of both probabilities and ranges improves at adequate
   effective N. A system that finds no edge says so (49A) and abstains rather than
   guessing.

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

**Macro exposure features (v2.2.0, ACR-106).** A security's measured sensitivity to a
macro factor (9C), applied to an observed move in that factor, is a company-level
feature in the Fundamental family and enters under standard admission (10, 11). It is
not a regime feature and does not inherit routing-only status. Raw macro levels and
changes remain regime features.

---

## 9B. Sector KPI Registry

A single fundamental feature set applied to every company discards most of what is
knowable about each. A bank's fundamentals are not a cement producer's. "Revenue
growth, margin, ROCE" applied uniformly is not neutrality; it is information loss.

Each sector carries a registered KPI schema. The schema is a versioned artifact and
is an input to adaptive evidence selection (30A.1).

| Sector | Core KPIs |
|---|---|
| Banks | NIM, GNPA, NNPA, provision coverage, credit cost, CASA ratio, slippage, capital adequacy |
| NBFC / HFC | AUM growth, spread, cost of funds, GS3, ALM mismatch, borrowing mix |
| Insurance | APE, VNB margin, persistency, combined ratio, solvency |
| IT services | Constant-currency growth, utilisation, attrition, deal TCV, offshore mix |
| Cement | Realisation per tonne, capacity utilisation, freight and power cost per tonne |
| Steel / metals | Realisation, volume, spread over input, integration level |
| Pharma | Segment-wise revenue, US ANDA pipeline, regulatory observations, R&D as share of sales |
| FMCG | Volume growth versus value growth, gross margin, A&P spend, rural mix |
| Retail | Same-store sales growth, sales per square foot, store additions |
| Telecom | ARPU, subscriber additions, churn, capex intensity |
| Auto / ancillary | Volume by segment, realisation, content per vehicle, order book |
| EPC / infrastructure | Order book, book-to-bill, execution cycle, receivable days, arbitration claims |
| Real estate | Pre-sales, collections, net debt, inventory months, launch pipeline |
| Hotels / hospitals | Occupancy, ARR or ARPOB, RevPAR |
| Utilities | PLF, tariff realisation, receivable days from discoms |
| Chemicals | Realisation, utilisation, product mix, environmental compliance status |

Rules:

1. Sector membership is point-in-time. Reclassification is an event.
2. A sector KPI is a fundamental feature and enters the registry under the same
   admission rules (10, 11). Nothing is exempt because it is conventional.
3. **Segment-level reporting is used wherever disclosed.** A conglomerate's
   consolidated margin is an average that hides the business.
4. Where a company spans sectors, the schema is the union, and the segment split is
   required rather than optional.

---

## 9C. Fundamental Factor Inventory

Beyond growth, margin and valuation. Grouped by what they measure.

### Earnings quality and forensics

Accruals ratio (total accruals scaled by assets), CFO-to-EBITDA and CFO-to-PAT
conversion, receivable days against revenue growth, inventory days trend, other
income as a share of PBT, effective versus statutory tax rate, contingent liabilities
against net worth, auditor fee ratio and non-audit fees, consolidated-versus-standalone
divergence, interest and cost capitalisation, change in accounting policy or estimate.

Interest and cost capitalisation matter disproportionately in Indian infrastructure
and real estate, where they are a common route to manufactured earnings.

### Capital allocation

**Incremental ROCE** — change in EBIT over change in capital employed — which says
what the marginal rupee of capital earns and is far more informative than the level.
Also: reinvestment rate, capex against depreciation, acquisition history and goodwill,
working capital intensity change, dividend and buyback consistency.

### Solvency and refinancing

Net debt to EBITDA trend, interest coverage, **debt maturity profile and the
refinancing wall**, unhedged foreign-currency debt, working capital facility
utilisation. The maturity wall, not the leverage level, is how Indian mid-caps
actually fail.

### Expectations

Consensus estimate revisions — direction and breadth — which is among the most
robustly documented cross-sectional signals in the literature. Standardised unexpected
earnings, post-earnings announcement drift, estimate dispersion.

**Management credibility, computed:** guidance tracked against subsequent actuals,
scored per company over time. This is the same machinery as the system's own
calibration (17) pointed at management, and it is rarely done systematically.

### Market microstructure

Turnover ratio, impact cost, bid-ask spread, **delivery percentage** (published by
NSE, and useful for separating delivery-based accumulation from intraday churn),
volatility term structure.

### Computed macro sensitivity

Betas to rates, INR, crude and specific input commodities, **measured from the
company's own history** rather than assumed from sector membership. Also export and
import revenue share, and input-cost pass-through lag.

v2.2.0 extends the factor list to the global context of 3G: US Treasury yields, the US
dollar index, world and regional equity indices, volatility indices, credit spreads and
aggregate foreign-investor flows. Each sensitivity is estimated point-in-time from data
available at the estimation date, over declared windows, and carries its estimation
error; an unstable estimate is recorded as unstable, not used.

### Disclosure text

Not sentiment — linguistic change detection. MD&A tone shift year over year,
risk-factor additions and deletions, disclosure length and complexity change, and from
earnings calls: analyst question concentration, and the ratio of answer length to
question length as an evasiveness proxy.

### Event-response history

How this specific security has historically reacted to each registered event type.
The same news means different things for different stocks, and the prior is
computable.

---

## 9D. Chart Patterns — Admission Path

Chart patterns are not excluded by this architecture. They enter through the same door
as every other feature (10, 11, 26), and that door has one requirement they usually
fail: a **deterministic definition**.

### 9D.1 Why the definition is the obstacle

"Head and shoulders" has no canonical specification. Two practitioners annotate the
same chart differently, and the same practitioner differs across two sittings. A
feature that cannot be computed identically twice cannot be point-in-time
backtested, cannot carry a stable trial count for DSR, and cannot pass the
reproducibility requirement in 14. The problem is not that patterns are worthless. It
is that an ambiguous definition makes the entire validation apparatus inapplicable.

### 9D.2 Admissible formalisations

A pattern feature is admissible when it is specified as code with declared
parameters:

| Approach | What it gives |
|---|---|
| Kernel-regression smoothing then local-extrema sequence conditions | The Lo, Mamaysky & Wang formalisation; peer-reviewed, explicit, reproducible |
| Perceptually Important Points / piecewise linear approximation | Pattern as a declared sequence of turning points with tolerances |
| Swing decomposition with an ATR-scaled threshold | Scale-invariant, parameterised, deterministic |
| Candlestick rules on OHLC | Already fully deterministic; trivially admissible |
| Matrix profile / shapelet discovery | **Preferred.** Discovers discriminative subsequences from the data instead of importing a named taxonomy |

Shapelet and matrix-profile discovery is the more self-learning option and fits this
architecture better than the traditional catalogue: it finds what is actually
predictive in your universe rather than testing whether a pattern named in the 1930s
happens to work.

### 9D.3 Search-space consequence

Pattern features are a large expansion — dozens of candlestick rules times horizons
times parameter choices, and shapelet discovery is unbounded by construction. Under
25A this is its own experiment family with its own declared budget and its own
validation allocation. Pattern discovery cannot draw on another domain's budget, and
the DSR trial count for any pattern includes the full search history of the family.

### 9D.4 No vision-model chart reading

Rendering price data to an image and asking a model to read it back is prohibited.

1. The chart is a lossy rendering of data the system already holds exactly.
   Everything visible in it is computable from the OHLCV series directly, without
   loss.
2. It breaks grounding (30B). A number inferred from pixels has no fact record to
   validate against, so the entire role-declaration gate becomes inapplicable.
3. It is not reproducible. Scale, log versus linear, window length and overlay choice
   change what the model sees. Same data, different chart, different answer —
   which fails 14.
4. Point-in-time cannot be enforced on an image. A rendering can silently include
   bars after the as-of date, and there is no schema on which to clamp (5A.2).

Read the series, never the picture. The series is strictly more information.

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

## 11. Economic Rationale and Methodology Preregistration

Preregistration applies to **methodology choices**, not only to feature rationale.

When a research choice has several defensible options — which benchmark defines
relative strength, whether broad and sector signals are separate or combined, how a
horizon resolves — the choice is made and frozen **before any comparative result is
calculated**. Choosing after seeing which option performed better is selection on the
outcome, and no downstream statistical control recovers from it.

The frozen record states the option chosen, the options rejected, the date, and that no
comparative values existed at the time. Where two variants are retained, they are
retained as **separate preregistered methodologies** evaluated independently — never as
a dynamic switch, and never with one falling back to the other when its route is
missing. A missing sector benchmark route blocks the sector feature; it does not
silently become the broad benchmark.

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

### 14.0 Investability floor

Breadth is necessary and not sufficient. A cross-section of 200 securities of which
half cannot be traded in meaningful size produces statistics that describe an
unreachable portfolio.

Every security in the research universe must clear a declared, point-in-time
investability floor before it contributes to any cross-sectional statistic:

**Primary policy — India-specific, versioned, empirically set:**

| Screen | Purpose |
|---|---|
| Free-float market capitalisation floor | Excludes names whose tradable float is too small regardless of headline size |
| Minimum median traded value over a declared window | Excludes names that cannot absorb a position |
| Minimum trading-day coverage in the window | Excludes intermittently traded names |
| Spread, slippage and impact estimate where available | Direct measure of execution cost |
| Surveillance stage, ban period and circuit status | Excludes mechanically constrained names |
| Price / penny-stock constraint | Excludes names where tick size dominates returns |
| Capacity estimate at the intended position size | Ensures the statistic describes a reachable portfolio |

**Secondary — robustness only:** the bottom-20%-by-size exclusion (25A.1), reported
alongside every cross-sectional result, never the production cutoff.

The primary thresholds are not assumed. They are set from real Indian data and then
frozen in the Methodology Registry with a version. Until they are set from evidence,
they are declared provisional and every statistic states which version it used.

Rules:

1. The floor is point-in-time. A security that was illiquid then is excluded from the
   cross-section then, whatever it looks like now.
2. Excluded securities remain in the survivorship-aware universe (6A.1) and in the
   delisting record. Investability exclusion is not deletion.
3. The floor's parameters are versioned; loosening it to reach a breadth threshold is
   a governance violation, not a tuning decision.
4. Every cross-sectional statistic reports the count before and after the floor.

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

Return-magnitude forecasts (7A, v2.2.0) are scored by pinball loss and CRPS and
calibrated by interval coverage; the bin and effective-N policy of section 17 applies to
the coverage rates.

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

The same state machine applies separately to return-magnitude ranges (7A rule 4,
v2.2.0).

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
return_quantiles            # 7A (v2.2.0): absolute and excess, by horizon, after costs
decision_rule_version       # 7A rule 5 (v2.2.0)
cost_model_version          # 22A (v2.2.0)
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

### 21.1 `UNRESOLVABLE` — claims that can never settle

A claim whose security delists, is suspended indefinitely, merges away, or whose
resolution source ceases to exist cannot be scored. If such a claim simply remains
pending and is retried forever, the resolved population becomes composed entirely of
securities that survived — reintroducing on the outcome side precisely the survivorship
bias that 6A.1 prevents on the data side. This is a real failure mode observed in
production systems, and it is silent.

Every claim therefore has a terminal disposition:

```text
RESOLVED        outcome determined
UNRESOLVABLE    cannot be determined, with a recorded reason
```

Recorded reasons include delisting, indefinite suspension, merger or amalgamation,
benchmark discontinuation, and target-definition failure.

Rules:

1. **Deterministic economic resolution is attempted first.** A delisting, merger,
   acquisition or scheme of arrangement usually has an official consideration, exit
   price, swap ratio or reference value. Where the outcome can be reconstructed from
   authoritative terms, the claim **resolves** using them. `UNRESOLVABLE` applies only
   where the outcome genuinely cannot be reconstructed.

   This ordering matters because adverse delistings are the cases most likely to be
   lost, and losing them biases the sample toward survivors — the exact failure this
   section exists to prevent.
2. A claim moves to `UNRESOLVABLE` when its resolution condition becomes permanently
   unmeetable **and** deterministic economic resolution has been attempted and failed.
   The attempt and its failure reason are recorded. A claim is never left pending
   indefinitely.
2. `UNRESOLVABLE` claims **count in the denominator** of coverage and completeness
   statistics. They are excluded from calibration numerators, and the exclusion is
   reported with its count.
3. The `UNRESOLVABLE` rate is monitored alongside `OUTPUT_REVIEW`, `unknown`
   attribution and `extraction_failure`. A rising rate concentrated in one part of the
   universe is a selection warning.
4. Where a delisting was itself the adverse outcome the thesis warned about, the claim
   resolves rather than becoming unresolvable. Losing the evidence of a correct bearish
   call is the worst version of this bias.

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
| 6M and 12M targets | Cost model still required for any **economic promotion**; sophistication may be reduced, and omission is permitted only under a documented materiality test |
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

**Every economic promotion carries an explicit, versioned cost and capacity model.**
The level of sophistication is proportionate; the existence of the model is not
optional. Omission is permitted only where a documented materiality test shows cost is
immaterial for that specific candidate, and the test is recorded with the promotion.

The gate keys on **turnover and capacity, not on target horizon.** A strategy with a
12-month target that rebalances monthly has monthly turnover, and a horizon-keyed rule
would let it escape the cost gate entirely. Turnover is computed from the candidate's
actual rebalancing behaviour, not inferred from its target.

This platform does not execute. Cost modelling exists to stop features looking
valuable when they are not.

---

## 22B. Risk Adjustment — Alpha, Not Repackaged Beta

A feature can predict returns and still be worthless, because the returns are
compensation for a known factor exposure that can be bought cheaply. Establishing
predictive power is not establishing value. This section is a promotion gate, not a
diagnostic.

### 22B.1 The requirement

Every candidate whose economic evaluation reports a return must have that return
regressed on a factor model. **Promotion requires a statistically significant
intercept.** A significant raw return with an insignificant intercept is a factor
exposure, and is rejected as a discovery.

### 22B.2 The factor model for Indian equities

The reference model is the four-factor Indian series — market, size, value, momentum —
maintained by IIM Ahmedabad (Agarwalla, Jacob and Varma). Two properties of that
library make it the right reference rather than a convenience:

1. It **excludes illiquid firms** so that the underlying portfolios are investable.
2. It **corrects for survival bias**, which its authors introduced specifically
   because of the frequency with which Indian public companies vanish.

Both align with controls this architecture already requires (6A.1, 14). The factor
series is a registered source under the Source Registry with its own version and
release cadence, and the factor-model version used is recorded on every evaluation.

### 22B.3 No risk-model shopping

Adding factors after observing that alpha survives — or disappears — relocates
researcher discretion from the signal into the risk adjustment, where it is harder to
see. The prohibition is absolute:

1. The **primary factor model is preregistered before the candidate is evaluated.**
2. **Robustness models are preregistered at the same time**, not selected afterwards.
   Where a candidate plausibly loads on low volatility, quality or liquidity, those
   models are declared up front.
3. **No factor is added post hoc because it changes the candidate's alpha.** Adding a
   factor after seeing the result is a new preregistration and a new evaluation, and
   the original result stands in the record.
4. Where the primary and robustness models disagree, the disagreement is **recorded**,
   not resolved by choosing. A candidate significant only under one preregistered model
   is reported as model-dependent.
5. A change to the reference factor model itself — a new factor added to the library,
   a methodology revision — is a model version change requiring re-preregistration of
   the evaluation, not an amendment to an existing one.

### 22B.4 Factor evaluation lineage

Factor histories are revised. Recording "IIMA four-factor" is not reproducible. Every
evaluation stores:

```text
factor_source_id
factor_model_id
factor_model_version
factor_release_date
raw_file_sha256
factor_loadings
alpha
alpha_t_stat
inference_method
preregistration_id
```

### 22B.5 The factor series is point-in-time evidence

The reference library publishes on a release cadence and revises history between
releases. A factor value for a past month as published in one release may differ in
the next.

Section 5B therefore applies to the factor series exactly as to any other source. The
release used is pinned by date and hash; a re-run reproduces the evaluation from the
pinned release, not from the current one; and an evaluation performed under one release
is not silently compared against one performed under another. Factor data enters the
Source Registry with its own availability semantics.

### 22B.3 Rules

1. No feature is promoted on unadjusted return.
2. The factor-model version and the estimated loadings are stored with the evaluation
   and are part of the promotion record.
3. Alpha is reported with its own t-statistic, subject to the hurdle in 25A.
4. A candidate whose alpha is insignificant but whose loadings are informative is
   recorded as a **factor proxy** — useful for exposure measurement, not admissible as
   a predictor.
5. Risk adjustment applies to the agent's aggregate output as well as to individual
   features (22C).

---

## 22C. Baseline Comparators

Calibration answers whether the system's confidence is honest. It does not answer
whether the system is useful. A well-calibrated system that adds nothing over a naive
rule is a well-calibrated waste of effort, and nothing in v2.0 would have detected
that.

Three standing comparators, computed on the same universe, the same horizons and the
same cost assumptions as the agent's own claims:

| Baseline | Definition |
|---|---|
| Index | Buy-and-hold of the registered broad benchmark |
| Equal-weight | Equal-weighted holding of the coverage cohort |
| Naive momentum | A simple 12-1 cross-sectional momentum rule, unoptimised |

Rules:

1. Baselines are computed for every evaluation window and reported alongside the
   agent's results. They are never omitted because the comparison is unflattering.
2. The naive momentum rule is **fixed at definition and never tuned**. A tuned
   baseline is not a baseline; it is another candidate consuming trial budget.
3. **Whether baseline comparison gates promotion depends on what the candidate
   claims:**

   | Candidate type | Requirement |
   |---|---|
   | Alpha / return-bearing feature | **Gate.** Must demonstrate incremental economic value over its preregistered relevant baseline |
   | Risk, state or calibration feature | Not gated on return. Must demonstrate incremental value for its **declared function** — variance explained, calibration improvement, regime discrimination |
   | Aggregate agent or strategy | **Gate.** Compared against all applicable baselines |

   The relevant baseline is preregistered with the candidate. A momentum-family
   candidate is measured against naive momentum, not against the index.
4. The comparison is made on risk-adjusted terms (22B), not raw return, and the
   baseline passes through the same cost model as the candidate (22A). Comparing a
   costed strategy against a costless baseline manufactures outperformance.
5. Failure to beat a relevant baseline blocks promotion of an economic claim. It does
   not retire the feature, which may still be admissible for its declared non-economic
   function.

---

## 22D. Signal Combination

Where several admitted features bear on the same target, their combination is
specified rather than left to the agent.

1. **The default is equal weighting** across admitted features. Out-of-sample,
   optimised weights typically underperform simple averaging, because the weight
   estimation is itself a fitting exercise on a short sample.
2. Any departure from equal weighting is a candidate in its own right: it is
   preregistered (11), consumes trial budget (25A), and must clear the validation
   stack.
3. Correlated features are combined within their redundancy group (12) before the
   groups are combined, so that three variants of one idea do not outvote one distinct
   idea.
4. The combination rule and its version are recorded on every prediction.
5. The agent does not set weights. Combination is deterministic code; the agent
   interprets the combined result and may argue against it, which is recorded as
   contradictory evidence (30A.2).

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

### 25A.1 The significance hurdle

Deflated Sharpe and PBO answer how much to discount a result. This states what the
result must reach.

**A newly discovered factor must clear a t-statistic of 3.0**, not the conventional
2.0. The reasoning (Harvey, Liu and Zhu, *Review of Financial Studies* 2016) is that
after hundreds of factors have been tested against the cross-section of returns, the
conventional threshold no longer carries its nominal meaning. Their own application of
the criterion is the number worth internalising: **of 313 return-correlated variables,
nine survive.** Their stated conclusion is that most claimed findings in financial
economics are likely false.

Companion controls:

1. **Size robustness screen.** Every cross-sectional result is additionally reported
   with the smallest 20% by market capitalisation excluded (after Hou, Xue and Zhang).
   A result that survives the primary investability policy (14.0) but disappears under
   this screen is recorded as size-dependent and is not promoted as a general finding.

   This is a **mandatory robustness test, not the production cutoff.** The 20%
   breakpoint is a US empirical result, and section 3E rule 3 of this document states
   that a prior established in another market is a weaker prior for Indian equities.
   Importing it as a mandatory Indian exclusion would contradict that rule. The
   production investability cutoff is set by the India-specific policy in 14.0 and is
   frozen in the Methodology Registry once real Indian data establishes what threshold
   yields sufficiently tradable portfolios.
2. **A candidate already in the prior library (3E) is not a discovery.** It enters with
   the literature's t-statistic as a prior and must justify itself against that prior,
   not against zero.
3. The hurdle applies to the **alpha** t-statistic (22B), not to raw return.
4. Where a result clears 2.0 but not 3.0, it is recorded as such and held. It is not
   rounded up, re-tested on a different window, or promoted with a caveat.

### 25A.2 Universe-level multiple testing

Repeatedly analysing the same coverage cohort is itself a form of multiple testing that
no per-candidate control captures. Thirty securities examined across years accumulate
implicit selection that never appears in any experiment ledger.

**What consumes trial budget is a choice made after seeing an outcome, not the act of
forecasting.** An unchanged model issuing a thousand live predictions has produced a
thousand observations and zero hypothesis tests. Counting them as trials would make the
budget meaningless and would penalise exactly the behaviour this architecture wants.

| Activity | Accounting |
|---|---|
| Routine forecasts from an unchanged model | **Observations.** Not trials |
| Outcome observed → methodology changed → retested | **Adaptive trial** |
| Coverage cohort reselected after seeing results | **Selection trial** |
| Feature, model or hyperparameter changed after inspection | **Research trial** |
| Same candidate re-tested on a different window after failing | **Research trial** |

Rules:

1. Trial budget is consumed by adaptive, selection and research trials. Observations
   are counted separately and are the input to calibration, not to the multiple-testing
   correction.
2. Findings that appear only within the coverage cohort and not in the wider research
   universe are flagged as cohort-specific and are not generalised.
3. Cohort composition changes are recorded as events with dated rationale; a finding
   does not survive a cohort change unaltered.
4. The distinction is enforced at the harness: a run that changes no registered
   artifact increments the observation counter; a run that follows a change to one
   increments the trial counter.

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

**Published factors enter with a decay prior.** A characteristic drawn from the prior
library (3E) is not treated as having a stable effect size: post-publication decay in
cross-sectional predictors is well documented, and the monitor's starting expectation
for such a feature is decline rather than persistence. A novel candidate has no such
prior and starts neutral. The distinction is recorded on the Feature Card and affects
the monitor's alert threshold, not its mathematics.

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

v2.2.0 adds global dimensions (3G, ACR-107):

- global risk appetite (risk-on / risk-off), from volatility indices and credit spreads
- US dollar and US rate direction
- commodity shock state, crude oil in particular
- foreign-investor flow state
- geopolitical stress, from the volume and tone of conflict coverage (4A.0)

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

### 34.1 ABSTAIN and OUTPUT_REVIEW are different outcomes

Naming note: this section's `OUTPUT_REVIEW` is unrelated to `AVAILABILITY_REVIEW` in
5B. One is a parse failure in agent output; the other is unproven data availability.
Earlier revisions called both `REVIEW`. Read `REVIEW` below as `OUTPUT_REVIEW`.

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
Decision per horizon: BUY / HOLD / SELL / ABSTAIN (7A, v2.2.0)
P(gain), P(outperform) and return range per horizon (7A, v2.2.0)
Global and macro context and the route by which it applies (3G, v2.2.0)
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
21. Decision per horizon (7A, v2.2.0)
22. Probability of gain and of outperformance per horizon (7A, v2.2.0)
23. Return range per horizon, absolute and versus benchmark, after costs, with its calibration state (7A, v2.2.0)
24. Global and macro context relevant to the security, with the route by which it applies (3G, v2.2.0)

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

**Acceptance is capability-specific.** A stage may close for a named capability while
other modes of the same stage remain explicitly false. This replaces the binary phase
gate stated in earlier revisions, which forced a stage to be either complete or not and
so pushed toward overclaiming.

A capability-specific acceptance states both halves:

```text
STATUS            : ACCEPTED_<CAPABILITY>_BASELINE
what is proven    : <enumerated, with counts>
what is NOT claimed:
  - <capability>  : False
  - <capability>  : False
```

The second list is not a caveat. It is half the acceptance, it is machine-readable, and
converting any entry to `True` without new evidence is a governance violation.

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
| 6a | Price-history acquisition (v2.2.0) | The research universe has point-in-time daily history long enough for every registered feature window and for at least two distinct regimes (14), from a source whose terms permit it (4G) |
| 7 | Fundamental Data Adapter | Consolidated and standalone never mix; basis is explicit on every fact |
| 8 | Corporate Event Adapter | Syndicated republication of one release collapses to one event |
| 9 | News / External Adapter | Extraction confidence is stored separately from investment confidence |
| 9a | Global and India Macro Context Adapter (v2.2.0) | Every series carries session, time zone, publication time and vintages; a foreign close is not available to an Indian decision before it exists (5C) |
| 9b | Macro and Geopolitical Event Adapter (v2.2.0) | An event without an issuer is never attributed to a security except through a declared, recorded route (4A rule 5) |
| 9c | Aggregate Investor Flows Adapter (v2.2.0) | Daily FPI/FII and DII flows are stamped with their publication time, never the trade date (3C rule 1) |
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

Steps 6a and 9a-9c (v2.2.0) are Services. They come before step 11 by owner decision
(ACR-108), because the evidence hub must hold the global context the Indian market
depends on. Each is built to a current-decision baseline first, so the vertical slice
(3F) is delayed as little as possible; their deeper capabilities remain non-blocking.

---

## 40C. Component Status Register

**Scope note (v2.2.0, ACR-112).** This register, section 49's status remarks and the
"Current implementation position (v2.1.1)" at the end of this document describe the
predecessor codebase at checkpoint `49d639bb2f174aa35f0a63746d3de88a3ff0ab3b`. The
repository `ai-equity-agent` is an independent build of this architecture (ADR-002); its
status is the set of acceptance records in `stages/*_acceptance.yaml`, summarised in the
position note that closes this document.

This register is the authoritative statement of what exists. It is updated as a diff,
and a component moves to "integrated" only when its 40B test passes on real data.

**Implementation baseline: checkpoint `49d639bb2f174aa35f0a63746d3de88a3ff0ab3b`.**

| Step | Item | Status |
|---|---|---|
| 1–11 | Registry, trust, PIT, universe, market, fundamentals, events, news, sentiment, hub | `CLOSED` on real NSE data |
| 10 | Sentiment | `CLOSED` as evidence pipeline; feature admission `DEFERRED` |
| 12 | Real Feature Factory | `ACCEPTED_CURRENT_DECISION_BASELINE` |
| 13 | Real Target Engine | **NEXT** — read-only contract probe first |
| 14–23 | Agent, ledger, shadow, resolver, attribution, calibration, drift, learning, specialists, API | `SCAFFOLD` — not operationally started |

Proven at Step 12: six real registered non-relative features with lineage; twelve
registered features after controlled migration; corporate-action-adjusted price history;
broad 6M cross-section of 1,905 securities and 12M of 1,484; wrong-benchmark rejection;
no held feature promoted.

Explicitly **not** claimed at Step 12: full point-in-time sector routing, historical
replay readiness, Effective N, feature admission, production agent readiness.

| Component | State | Next action |
|---|---|---|
| Feature Card / Registry | Integrated (Step 12) | Enforce preregistration rejection (11) |
| Target Registry / Engine | Prototype | Connect real targets and point-in-time benchmark definitions |
| Research dataset / panel | Prototype on synthetic | Replace synthetic panels with trusted real data |
| Effective-N / statistics | Prototype | **Revalidate on real dependency structures** — synthetic panels have clean dependence; real ones do not |
| Purged / CPCV / WFA / holdout | Prototype | Align purge windows to actual target horizons |
| Multiple testing / experiment ledger | Prototype | Connect to automatic family tracking per domain (25A) |
| Economic evaluation | Prototype | Add cost and impact model before any ≤30D promotion |
| Lifecycle / promotion | Prototype | Bind to human approval and real evidence |
| Shadow evaluation | Prototype | Merge into the authoritative ledger with `origin` |
| Data Trust / ingestion | **Integrated, Steps 2–6** | No further foundation work required |
| News / events / sentiment | **Integrated, Steps 8–10** | Sentiment feature admission deferred (10) |
| Knowledge / Event Hub | **Integrated, Step 11** | Five-domain real evidence |
| Corporate-action adjustment | **Integrated, Step 12** | Narrow V1 scope; remainder fail-closed (6C) |
| Benchmark Registry | **Integrated, Step 12** | Sector routing deferred |
| Equity Research Agent | `SCAFFOLD` | After Step 13 target contract |
| Calibration / attribution / learning | `SCAFFOLD` | After shadow predictions accumulate |

Rows marked integrated refer to the accepted real-data implementation and must not be
reverted to a planning state. Any row claiming a built component is "not built" is
stale by definition and is a document defect, not a status.

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
| No chart rasterisation | Assert no module imports an image library on a path reachable from feature computation or agent context |
| Leakage features are fenced | Assert every feature flagged as leakage-derived is absent from the feature set of any event-tied directional target |

### 40D.1 Negative-assertion acceptance

An acceptance test that only checks what happened cannot detect a control that silently
stopped working. Every stage acceptance therefore asserts, explicitly, what did **not**
happen.

Illustrative negative assertions from the accepted implementation:

```text
raw model output changed          = False
polarity auto-corrected           = False
source reputation invented        = False
missing spam score invented       = False
missing novelty invented          = False
arbitrary downweight applied      = False
feature created                   = False
production core modified          = False
historical PIT claimed            = False
held feature promoted             = False
```

A run of `False` values here is the **success** condition. These assertions are part of
the accepted artifact and are re-run on every change to the stage.

The same pattern applies to capability flags: an unresolved capability is recorded as
explicitly false rather than omitted. Omission reads as completeness; `False` reads as
a boundary.

Rules for this section:

1. These tests run in CI on every commit, not on a schedule.
2. A test here is never marked expected-to-fail to unblock work. The rule is either
   enforced or removed from the architecture.
3. When a leak or violation is found in operation, the fix includes a static test
   that would have caught it. A fix without a test is not complete — this is how a
   leakage class stops recurring.

---

## 40E. Tooling Errors Are Not Production Defects

A failing probe, audit or inspection script is evidence about the script until the
script is verified. In the accepted implementation this pattern recurred repeatedly: a
header-case mismatch in a reconciliation script reported zero matches; an audit failed
at report generation because a helper was omitted; a validation script checked a field
name that did not exist in the contract; a BOM warning suggested a source defect that
parsing proved absent; a probe searching for a literal in the wrong module reported a
contract as unused when it was created downstream.

In every case the production code was correct.

Rules:

1. **No production mutation is made on the strength of a probe result until the probe
   itself has been verified.**
2. Audit and inspection scripts are read-only until reviewed. An audit that can mutate
   is not an audit.
3. When a probe and the production contract disagree, inspect the probe first.
4. A fixed probe is re-run before any conclusion is drawn from its earlier output.
5. Tooling failures are recorded as tooling failures in the stage record, not as
   architecture defects.

The inverse also holds: a probe that reports success proves only that the probe ran.
Structural self-tests and real-data acceptance are separate milestones.

---

## 40F. Migration Protocol for Existing Contracts

Renaming or replacing an established identifier is the most common source of
unnecessary regression in a system of this shape.

### 40F.1 Dependency-impact audit precedes any change

Before modifying a registry entry, contract or identifier, a read-only audit
establishes the reference count, the call sites, whether any caller passes arguments
positionally, and which tests bind to the current behaviour. In the accepted
implementation this audit found roughly 164 references to two feature identifiers that
a rename would have broken, and separately established that a contract could take a new
optional field safely because none of its six call sites passed positionally.

### 40F.2 Prefer a binding layer to a rename

Where new identities are needed, preserve the existing ones and introduce a controlled
binding layer that maps new external identities onto the existing verified mathematics.

The binding must be proven **mathematically equivalent** to the direct path before use,
and the underlying engine is left unmodified. New identities enter as `HELD` and are
promoted only through the normal admission route.

### 40F.3 Prove the contract outside production first

Where two existing modules each implement part of a required contract, build the
combined contract as a prototype outside the production core and prove it there before
refactoring either. A prototype that correctly produces **zero** outputs — because every
input was properly refused — is a successful proof.

---

## 40G. Build Order and Acquisition Boundaries

### 40G.1 No downstream module without the upstream spine

Research infrastructure built ahead of the data spine creates the appearance of a system
where none exists. In this project's own history, roughly 62 core modules and 50,000
lines of downstream research code existed — feature registries, target engines,
statistical evaluators, CPCV, holdout, promotion logic, agent scaffolds, prediction
ledger, calibration — while the real end-to-end exchange path was still incomplete.

Rules:

1. A downstream stage is not started until the stage it consumes is accepted.
2. Existing ahead-of-sequence code is reclassified as `SCAFFOLD`, not deleted and not
   counted as progress.
3. "Module exists" never means "stage complete."
4. Work that drifts ahead of sequence is parked, not continued, and the current stage is
   closed first.

One qualification, learned rather than assumed: **governance and scientific controls are
the exception and should be built early.** Building leakage, multiple-testing, holdout
and calibration controls before automated feature search means the search cannot outrun
them. Everything else follows the spine.

### 40G.2 Acquisition boundaries change; methodology does not

A source endpoint that changes format, rate-limits, or returns an unexpected content
type is an **acquisition-boundary** problem. Fix the request contract, add retry and
backoff, correct the parser.

Never respond by changing the research methodology, relaxing payload validation,
loosening a quality gate, or reducing a feature's lookback requirement. In the accepted
implementation an index endpoint changed and returned HTML instead of JSON; the request
protocol was corrected and the frozen benchmark methodology was left untouched. A
separate source rate-limited; backoff was added and validation was not weakened. A
lookback was short; history was acquired rather than the window shortened.

Record the acquisition contract with a version marker so a later change is detectable
rather than mysterious.

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
- López de Prado — Advances in Financial Machine Learning, including purging, embargo and combinatorial purged cross-validation

### Multiple testing and significance

- Harvey, C. R., Liu, Y. and Zhu, H. "…and the Cross-Section of Expected Returns." *Review of Financial Studies* 29(1), 2016, 5–68. The t > 3.0 hurdle; of 313 return-correlated variables, nine survive it.
- Hou, K., Xue, C. and Zhang, L. — exclusion of the smallest 20% by size in cross-sectional evaluation.
- Arnott, R., Harvey, C. R. and Markowitz, H. "A Backtesting Protocol in the Era of Machine Learning." *Journal of Financial Data Science* 1(1), 2019, 64–74.

### Prior-literature library (3E)

- Chen, A. Y. and Zimmermann, T. "Open Source Cross-Sectional Asset Pricing." *Critical Finance Review* 11(2), 2022, 207–264. Code: github.com/OpenSourceAP/CrossSection. Data: openassetpricing.com. Signal index: SignalDocumentation.xlsx.
- Chen, A. Y. and Zimmermann, T. "Publication Bias in Asset Pricing Research." arXiv:2209.13623.

### Indian factor model (22B.2)

- Agarwalla, S. K., Jacob, J. and Varma, J. R. "Four Factor Model in Indian Equities Market." IIM Ahmedabad Working Paper 2013-09-05. Data library: faculty.iima.ac.in/iffm/Indian-Fama-French-Momentum/ — market, size, value and momentum factors for Indian equities from January 1994, daily/monthly/yearly, illiquid firms excluded for investability, corrected for survival bias.
- Agarwalla, S. K., Jacob, J. and Varma, J. R. "Size, Value, and Momentum in Indian Equities." *Vikalpa* 42(4), 2017, 211–219. Includes factor drawdown tables — the momentum factor's worst drawdown was 63% over 5.1 years.
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
5. This document is **frozen at v2.2.0** (previously v2.1.1). Further quality comes from implementation
   evidence, not from continued architecture revision. An amendment requires a factual
   correction, a security or compliance requirement, an evidence-driven defect found
   during implementation, or a human-owned methodology decision changing an
   authoritative contract. Blueprint improvement in the absence of new evidence is no
   longer a reason to revise.
6. Where this document and the accepted implementation record disagree about a stage
   that has been built, **the implementation record is authoritative**. This document
   is amended to match it, not the reverse. Implementation inconvenience alone is never
   grounds to amend the architecture; implementation *evidence* always is.

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
54. Shareholding and ownership facts are stamped with filing date, never period end.
55. Derivatives features are expiry-aware and restricted to point-in-time F&O membership.
56. Leakage features are excluded from directional targets tied to the event they precede.
57. Private tip channels are an excluded source class in the Source Registry.
58. Every covered security resolves to a sector KPI schema; segment data is used where disclosed.
59. No pattern feature is admitted without a deterministic, parameterised definition in code.
60. No pipeline path renders market data to an image for model consumption.
61. Every availability decision resolves to ELIGIBLE, NOT_ELIGIBLE or AVAILABILITY_REVIEW; unknown never defaults to eligible.
62. Current-decision eligibility never implies historical-replay eligibility.
63. Unsupported corporate actions block the affected security-feature window only, never the universe, and never approximate.
64. No adjustment factor is derived from an observed price jump.
65. Identity bridges are event-scoped and evidence-backed; no symbol-only bridge and no global ISIN equivalence.
66. Sentiment features use sentiment-eligible stories only; attention features declare their story set.
67. Raw model outputs are never altered after inspection; conflicts are recorded instead.
68. Methodology choices are frozen before any comparative result is computed.
69. Every stage acceptance carries negative assertions and an explicit not-claimed list.
70. No production change is made on an unverified probe result.
71. Identifier changes are preceded by a dependency-impact audit; binding layers are preferred to renames.
72. No feature is promoted on unadjusted return; promotion requires a significant factor-model intercept.
73. The alpha t-statistic clears 3.0; results between 2.0 and 3.0 are recorded and held.
74. The smallest 20% by market capitalisation is excluded from cross-sectional evaluation.
75. Every security in a cross-sectional statistic clears the point-in-time investability floor.
76. Index, equal-weight and naive-momentum baselines are reported for every evaluation window.
77. Signal combination defaults to equal weighting; any alternative is a preregistered candidate.
78. Every claim reaches a terminal disposition; none remains pending indefinitely.
79. Cohort selection is preregistered, dated and mechanical.
80. Every candidate is checked against the prior-literature library before admission.
81. The primary and robustness factor models are preregistered before evaluation; no factor is added post hoc.
82. Every factor evaluation stores source, model version, release date and file hash.
83. The bottom-20% size exclusion is a reported robustness screen, never the production cutoff.
84. Baseline outperformance gates promotion of economic-alpha claims and aggregate strategy claims only.
85. Baselines pass through the same cost model as the candidate.
86. Routine forecasts from an unchanged model increment observations, not trials.
87. Every economic promotion carries a versioned cost and capacity model keyed to turnover.
88. Deterministic economic resolution is attempted before any claim becomes UNRESOLVABLE.
89. No non-blocking capability delays the Step 13–16 vertical slice.
90. Every market series records exchange, session calendar and time zone; availability is the time the value was set or published, in UTC, never its calendar date (5C).
91. No foreign close is available to an Indian decision before its session has ended (5C).
92. Economic releases are stored with every vintage; a series without vintages is withheld from historical replay (3G, 5A.1).
93. Foreign indices, yields and prices are never covered securities, targets or benchmarks for Indian claims (3G).
94. Raw macro levels are regime features only; macro exposure enters a claim only through measured company sensitivity admitted under the normal route (9A, 9C).
95. A macro, policy or geopolitical event is attributed to a security only through a declared, recorded route (4A rule 5).
96. Every registered source records its terms check; no source is used against its terms (4G).
97. A paid source is adopted only after a free source is shown insufficient and the owner approves (4G).
98. Only the declared network module opens connections, only to allow-listed addresses, without following redirects (4G).
99. No API key or password appears in chat, the repository, logs, stored URLs or error messages (4G).
100. Every claim carries P(gain), P(outperform), absolute and excess return ranges after costs, a decision and an invalidation condition for its registered horizon (7A).
101. Return ranges are scored by pinball loss and CRPS and calibrated by interval coverage, reported separately from Brier scores (7A, 16).
102. A return range that fails calibration is withheld; direction alone or ABSTAIN is shown (7A, 18).
103. The decision rule is a preregistered, human-owned, versioned artifact recorded on every claim (7A, 35).
104. Outputs are research for the owner's own decisions and are not distributed as advice (3).

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
17. No foreign or macro value in a decision before it existed in India time (5C).
18. No return figure without its range, its probabilities and its calibration state (7A).
19. No data source used against its terms, and no secret outside the owner's machine (4G).
20. No macro factor as a standalone buy or sell signal (3G rule 3, 9A).

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

## Current implementation position (v2.1.1)

*Predecessor codebase - see the scope note in 40C (ACR-112).*

Steps 1 through 11 are `CLOSED` on real NSE data. Step 12 is
`ACCEPTED_CURRENT_DECISION_BASELINE` at checkpoint
`49d639bb2f174aa35f0a63746d3de88a3ff0ab3b`. The data, evidence and feature
foundation exists and must not be rebuilt.

**The next development action is Step 13 — Real Target Engine, beginning with Stage
13A v2: a read-only contract probe.**

The existing Stage-13A script is not run unchanged. It was written against Architect
v1.5, its payload still names that governing target definition, and it predates the
controls adopted since. A replacement probe is written first.

Stage 13A v2 inspects, without modifying anything:

- registered target IDs and horizon definitions
- exact `TargetEngine.calculate()` semantics and forward-return behaviour
- target card and result contract fields
- whether the target layer carries an independent benchmark definition competing with
  the authoritative Benchmark Registry (a standing concern, not yet confirmed)
- whether long-horizon month handling approximates rather than using a proven
  exchange-session calendar (the second standing concern)
- coverage of 5D/10D/20D/30D, 60D/90D/120D, 6M/12M+ and event-specific targets

and additionally inventories the dependencies this architecture has since added:

- benchmark-version-at-claim resolution (14A)
- corporate-action semantics in target windows (6C.1)
- delisting and merger resolution, including deterministic economic resolution (21.1)
- risk-model interface for factor-adjusted evaluation (22B)
- baseline comparator interface (22C)
- investability screening at target construction (14.0)

Sequence: **13A probe → review → 13B impact audit → 13C human-owned methodology
freeze → minimum code change.** No target code is written before 13A completes.

In parallel, and deliberately not after: begin the Equity Research Agent v0.1 (step
14) as soon as steps 6 and 12 can feed it, and put it into `SHADOW_LIVE` immediately.
Shadow evidence accumulates from the day it runs, and the effective-N floors in
sections 15 and 22 mean that clock is the binding constraint on everything downstream.

Do not connect RD-Agent, do not begin autonomous feature optimisation, and do not
promote any feature until the statistical layer has been re-validated on real
dependency structures.

---

## Current implementation position (v2.2.0, repository ai-equity-agent)

Accepted in this repository, each with an acceptance record and an explicit not-claimed
list in `stages/`: 40B steps 2 to 8 (Stages 2 to 9) and step 9 (Stage 10, news
headlines from GDELT; Stage 10B, SEBI releases). Price history covers only weeks, so
step 6a is open.

Next, in order: step 9a (Global and India Macro Context), 9b (Macro and Geopolitical
Events), 9c (Aggregate Investor Flows), then step 10 (Sentiment) and step 11
(Knowledge/Event Hub), and the remaining steps in 40B order. Step 6a runs alongside as
sources are approved. Every source is chosen under 4G - official and free first, paid
only on the owner's approval.
