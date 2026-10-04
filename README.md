# AI Equity Research Agent

Self-learning equity research system for NSE, built in stages.

Governing architecture (FROZEN): docs/Master_Architecture_v2_2_0_FROZEN.md
(PDF copy, generated from it and never edited: docs/Master_Architecture_v2_2_0_FROZEN.pdf)
Earlier baselines, kept for history: docs/Master_Architecture_v2_1_1_FROZEN.md,
docs/Master_Architecture_v1_11.md

This repository is an independent build (see docs/decisions/ADR-002).
Stage status lives in stages/*_acceptance.yaml - what is proven, and what is NOT claimed.

Data notices:
- This product uses the FRED&reg; API but is not endorsed or certified by the Federal Reserve
  Bank of St. Louis. Series owned by others keep their owners' terms; data from FRED is stored
  privately for the owner's own research and never redistributed (docs/decisions/ADR-008).
- News metadata: The GDELT Project, https://www.gdeltproject.org/ (ADR-005).
- India macro statistics: Source - Ministry of Statistics and Programme Implementation (MoSPI),
  National Statistics Office, eSankhyiki (ADR-009).
- Market calendars generated with exchange_calendars (Apache License 2.0; licence text in
  docs/third_party/exchange_calendars-LICENSE.txt).
