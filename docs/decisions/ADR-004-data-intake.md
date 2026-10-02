# ADR-004 - Data intake: hand downloads from NSE, no scraping, licensed sources for scale

- decision_id: ADR-004
- date: 2026-10-02
- problem: Hand downloading does not scale - the agent will need results for about
  2,000 companies over many quarters. The owner asked for a scraper. NSE's Terms of
  Use (updated 29-Oct-2025) prohibit "systematic or automated data collection
  activities (including scraping ...)" and let NSE block access and take action.
  robots.txt allows crawling, but the terms bind the user.
- options: (1) scrape NSE's website, its APIs or its archive; (2) keep hand downloads
  and remove the clerical work around them; (3) a licensed source - NSE Data &
  Analytics, or a vendor or broker API whose terms allow programmatic use;
  (4) written permission from NSE.
- decision: (2) now; (3) or (4) to be chosen for scale. No module opens a network
  connection to collect data - enforced by a static test (Stage 8C). Third-party
  libraries that scrape NSE are not used.
- reason: owner decision after reviewing NSE's terms. Respecting a source's terms is
  part of provenance - the source registry records each licence (section 2). A
  blocked IP or a legal claim would stop the project.
- impact: a person downloads. 'checklist' writes one page of links to the files still
  missing; 'ingest-inbox' moves downloads into data/inbox and loads them in dependency
  order; a results file waits until its listing is loaded so its publication time is
  never lost (5B). A licensed source will be added as a new adapter with its terms in
  config/sources.yaml, and cross-checked against hand-downloaded NSE files (section 4).
- supersedes: none (extends the manual-download choice made at Stage 7A)
- owner: project owner
