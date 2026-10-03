# ADR-007 - Architecture v2.2.0: global and macro factors, return forecasts, data policy

- decision_id: ADR-007
- date: 2026-10-03
- problem: The owner asked whether the system accounts for everything that moves Indian
  stocks - global news, oil, wars, China, Japan and US markets, bonds and Treasuries,
  sovereign ratings - as well as technical and fundamental factors, and whether it can
  say which stock to buy, hold or sell, with the percentage gain to expect over a chosen
  number of days or months, and keep improving. A full review of v2.1.1 found:
  (1) the Sector/macro domain is Core (3B) but no 40B step builds it, although step 11
  must hold all domains; (2) the registered event types (4A.0) are company-level only -
  no central-bank, fiscal, trade, sovereign-rating, geopolitical or index-provider events;
  (3) world markets are not named; (4) there is no rule for markets that close at
  different hours, so a US close could leak into an Indian decision of the same date;
  (5) the ledger requires an expected value and a distribution (21) but nothing scores or
  calibrates return magnitudes, and no rule maps a forecast to BUY / HOLD / SELL;
  (6) sections 40C and "Current implementation position" describe the predecessor
  codebase (already noted in ADR-002).
- options: (1) keep v2.1.1 and handle these case by case; (2) amend the architecture as
  a patch under section 46, keeping every existing control.
- decision: (2). Master Architecture v2.2.0 adds, by insertion only:
  ACR-103 global and India macro context (new 3G, 3B rule 4); ACR-104 cross-market
  timing (new 5C); ACR-105 macro, policy and geopolitical event types (4A.0, 4A rule 5);
  ACR-106 macro exposure features via measured company sensitivity (9A, 9C); ACR-107
  global regime dimensions (29); ACR-108 steps 6a, 9a, 9b, 9c before step 11 (40B, 3F);
  ACR-109 data acquisition and network policy (new 4G); ACR-110 return-magnitude
  forecasts and a preregistered decision rule (new 7A, 16, 18, 21, 36, 37); ACR-111
  purpose and use (3); ACR-112 factual correction on 40C (folds in ADR-002); ACR-113
  acceptance criteria 90-104 and guardrails 17-20.
- control audit (46A rule 4): 4,152 lines of v2.1.1 -> 4,453 lines of v2.2.0;
  303 lines inserted, 0 deleted, 2 declared replacements (the version line and the
  'frozen at' line); all 210 headings, every ACR id and acceptance criteria 1-89 kept;
  tests/test_architecture_baseline.py repeats this audit in CI on every commit.
- reason: owner decision (2026-10-03): "include all of these changes into our architect
  and freeze it new final version that we have to follow", building an institutional-
  level model for the owner's personal recommendations.
- impact: the next builds are Stage 10C (step 9a, macro context), 10D (step 9b, macro and
  geopolitical events), 10E (step 9c, investor flows), then Stage 11 (step 10, sentiment)
  and step 11; step 6a (price history) runs alongside as sources are approved. The start
  of the effective-N clock moves later (3F); each added step is built to a
  current-decision baseline first. Sources follow 4G: free and official first; a paid
  plan only after the free one is shown insufficient and the owner approves it.
  docs/Master_Architecture_v2_2_0_FROZEN.pdf is generated from the Markdown and is never
  edited (46A); v2.1.1 is kept for history.
- supersedes: none (v2.1.1 remains in docs/ as history; ADR-002 stays in force)
- owner: project owner
