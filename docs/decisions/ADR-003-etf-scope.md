# ADR-003 - ETFs and mutual-fund units are out of scope for equity prices

- decision_id: ADR-003
- date: 2026-10-02
- problem: The first real NSE bhavcopy (2026-10-01) had 349 rows in the EQ
  series whose ISINs start with INF - ETFs and mutual-fund units. They are not
  companies, are not in NSE's equity list, and were quarantined at entity
  resolution. Quarantine is a defect signal; 349 non-defects a day would hide
  real defects.
- options: (1) keep quarantining them; (2) declare them out of scope;
  (3) model ETFs as a separate instrument class.
- decision: (2). The equity price adapters exclude ISINs starting with INF,
  as a written scope rule recorded on every run (adapter version 2).
- reason: owner decision (section 35: methodology is human-owned). Equity
  research covers company shares. NSE's file marks ETFs and shares the same
  way (series EQ, type STK); the ISIN prefix is the only mechanical difference.
- impact: excluded rows are counted as out of scope, not quarantined. No
  validation check was loosened (40G.2). ETFs can be added later as their own
  instrument class through an architecture change request.
- supersedes: none
- owner: project owner
