# ADR-010 - Central banks' feeds, FRED's release calendar, and routes for macro events

- decision_id: ADR-010
- date: 2026-10-04
- problem: Stage 10D (architecture 40B step 9b, 4A.0, 4A rule 5) needs macro, policy and
  geopolitical events - central-bank decisions, data releases, regulation, budgets, elections,
  conflicts - and a rule that keeps such an event, which has no issuer, from being attributed to a
  security except through a declared, recorded route (acceptance criterion 95).
- research (2026-10-04; terms read in the browser; one read of each feed and 8 FRED requests run by
  the owner with their key, all approved by the owner):
  - Federal Reserve Board: information on its site is in the public domain unless otherwise
    indicated, may be copied without permission, and the Board is to be cited; no robots.txt. Its
    monetary-policy feed (RSS 2.0) keeps about 15 items over six months; FOMC statements are always
    titled 'Federal Reserve issues FOMC statement' with the release time (18:00 GMT, 2 pm New York).
  - European Central Bank: free use of information obtained directly from its site, reproduced
    accurately with the ECB cited; modification stated; robots.txt asks for 5 seconds between
    requests. Its press feed keeps 15 items (about ten days); a monetary policy decision carries the
    document code 'mp' (ecb.mp260910~...), released at 14:15 Frankfurt time. Its certificate chains
    to Sectigo Public Server Authentication Root E46, which is in Mozilla's list of trusted roots
    (SHA-256 C90F26F0FB1B4018B22227519B5CA2B53E2CA5B3BE5CF18EFE1BEF47380C5383, valid 2021-2046) but
    was not loaded in the owner's Windows root store, so Python refused the connection.
  - Bank of Japan: content may be copied or reproduced with the Bank credited, except for commercial
    purposes and images. Its English what's-new feed keeps about 47 items (four weeks), mostly
    statistics; statements on monetary policy are files k<yymmdd><letter>. On 18-Sep-2026 (a
    policy-rate change) the feed carried only the '(Reference)' statement, not the main one.
  - FRED's release calendar (api.stlouisfed.org, already allowed): release/dates lists past and
    future dates per release, dates only. CPI, Employment Situation and GDP dates agree with the
    ALFRED first-release dates already stored (CPI for August 2026 on 2026-09-11). The late-2025 US
    shutdown moved CPI from November to 2025-12-18. 'FOMC Press Release' lists every day of the year
    and cannot serve as a meeting calendar.
  - PIB's feed holds only the latest 20 releases, without dates or ministries - too thin for a daily
    read; not used. RBI stays out (ADR-006). Rating agencies are licensed; GDELT topic searches wait
    until the owner's first GDELT fetch succeeds.
- options: (1) events only from data already stored; (2) plus the official central-bank feeds;
  (3) plus GDELT topic searches now; for what no feed carries: (a) nothing; (b) a list declared by
  the owner, citing public sources.
- decision: (2) and (b), approved by the owner on 2026-10-04 ("All three", "Your list now, GDELT
  later", ECB root "for the ECB only", replay "issuer's own time"):
  - src/ingestion/news_fetch.py may also ask exactly https://www.federalreserve.gov/feeds/press_monetary.xml,
    https://www.ecb.europa.eu/rss/press.html and https://www.boj.or.jp/en/rss/whatsnew.xml - each at
    most once an hour, no redirects - and FRED's /fred/release/dates for releases 10, 50 and 53 with
    the owner's key;
  - for www.ecb.europa.eu only, the public root Sectigo Public Server Authentication Root E46 is
    added to the trusted roots after its fingerprint is checked against the published value;
    certificates and host names stay checked for every host and no code switches checking off;
  - every read is kept byte for byte; a feed that is not RSS 2.0, declares a DOCTYPE or ENTITY, or has
    no items is refused whole;
  - an item counts for current decisions from this system's first read; for historical replay the
    issuer's own stated release time counts, when it carries a time of day and a zone and is not
    later than our read - as NSE's dissemination time does;
  - types come only from the issuer's own words (rule me-types-1); one meeting is one event (rule
    me-dedup-1); first releases of declared US and India statistics and SEBI's circulars become events
    from data already stored (rules me-releases-1, me-sebi-1); surprise against consensus is never
    assessed - no licensed consensus exists;
  - config/declared_events.yaml holds events declared by the owner, each citing a public source (never
    an rbi.org.in address); recorded once, never silently changed, current decisions only;
  - config/event_routes.yaml holds routes declared by the owner; only read_across routes can be
    recorded until a point-in-time sector classification (9B) or a measured sensitivity (9C) exists -
    the database refuses the other kinds; an event reaches a security only through a recorded route,
    the evidence is tagged read-across and never a direct observation, and its effect is never
    assumed;
  - attribution "Sources: Board of Governors of the Federal Reserve System; European Central Bank
    (this information is available free of charge at www.ecb.europa.eu); Bank of Japan." is printed by
    fetch-events and show-macro-events and kept in README.md.
- reason: official, free sources whose terms allow this personal, non-commercial use; exact release
  times from the issuers themselves; and a route rule that makes attribution an explicit, recorded
  human decision instead of a guess from a headline.
- impact: fetch-events sends 3 feed reads and 3 FRED requests a day. Not covered: BoJ meetings whose
  statements never appear in the English feed; ECB and BoJ meeting schedules; RBI decisions, budgets,
  elections, conflicts and ratings unless the owner declares them; GDELT topic searches (later step);
  times of day of US releases; direction and size of policy changes.
- supersedes: none (adds to ADR-005, ADR-006, ADR-008 and ADR-009)
- owner: project owner
