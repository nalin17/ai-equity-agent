# ADR-012 - Knowledge/Event Hub: every domain as one point-in-time evidence object

- decision_id: ADR-012
- date: 2026-10-05
- problem: 40B step 11 - "all domains normalise to one point-in-time evidence object". Stages 7-10E built
  one query per domain (prices, reported figures, announcements, corporate actions, SEBI, news, FRED,
  MoSPI, central-bank and release events, the release calendar, FII/DII flows), each with its own shape.
  The feature factory, the target engine and the research agent (steps 12-14) need one shape, with point in
  time, missing data and provenance carried the same way everywhere, and every claim traceable to a stored
  row (step 14).
- options: (1) a new evidence table filled by copying every domain - a second store that can drift from the
  first and must be kept append-only and versioned; (2) a read-only layer over the domains' own
  point-in-time queries, normalising their answers at the decision time; (3) leave each consumer to read
  each domain.
- decision: (2), with the owner's go-ahead on 2026-10-05 ("Knowledge/event hub yes, ... then choose further";
  the Sentiment Adapter, 40B step 10, comes next):
  - src/knowledge/evidence.py defines Evidence (evidence_id = '<table>:<key>' of the stored row; domain of
    3B/3C; kind; subject = an ISIN or 'context:<scope>'; attribution direct / route / context; observed day;
    available_at; claim; value or None with its missing-data class; unit; source; extraction confidence;
    routes; details), EvidenceGap (not built / withheld / degraded / missing / excluded, with the reason)
    and Bundle. A record that breaks a rule is refused, never repaired: a value with a missing class, an
    absent value without one, context evidence about a security, market/figures/corporate events as context,
    a security reached by an event without an issuer except through recorded routes, a time without a zone,
    a loose date, an extraction confidence that is not a registered reading. A bundle refuses evidence
    known after its decision time or judged under another claim.
  - src/knowledge/hub.py gather(conn, decision_time, claim, isin=None, start=None, end=None) reads only. Each
    domain's own query decides availability (5B); the hub never re-derives it. available_at is our retrieval
    under current-decision use and the source's proven publication time under historical replay.
  - The window is enforced (5A.2): the end clamps to the decision date (India time); a window wholly after it
    moves back with its span kept; unreadable bounds fall back to the decision date; default 30 days.
    Reported figures are not windowed; corporate actions and release dates may lie ahead (known in advance);
    the newest value of each series is given under its own date even when older than the window.
  - A security's bundle holds its prices, figures, announcements (one release = one event), corporate
    actions, SEBI releases naming it, news stories proven to name it (searched-only stories are left out and
    counted - 4B rule 3) and the events without an issuer that reach it through recorded routes - given once,
    as routed, never again as context (4B rule 5). Context (series, flows, events, the release calendar) is
    never attributed to a security (3G).
  - Gaps are always given (4E, 30A.2): public sentiment, derivatives positioning and alternative data have no
    adapter; evidence withheld for want of proven availability is counted; NSE trading days with no prices
    or no flows file are listed (extraction failure, never filled); a news store not yet read is degraded,
    not a crash.
  - manage.py show-evidence [SYMBOL|ISIN] [FROM] [TO] [--replay] prints counts per domain, the newest items
    and every gap.
  - tests/test_stage10d_macro_events.py: the guard that only the route module attributes events now names
    exactly two files - the route module, and the hub, which calls it and attributes nothing itself.
- reason: one source of truth per domain, no copy to drift; point-in-time and missing-data rules stay where
  they were proven; the shape is the contract steps 12-14 build on; the missing domains are said every time,
  so no factor is silently absent.
- impact: no new source, network access, table or migration (schema stays 20). Not yet: evidence selection
  per prediction (30A.1 - a registered policy, step 14), contradiction sets (30A.2 - the agent's), sentiment
  (step 10), adjusted prices in the bundle (the raw series is given; adjustment stays in features).
- supersedes: none
- owner: project owner
