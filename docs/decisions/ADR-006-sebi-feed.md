# ADR-006 - SEBI's RSS feed read by the program; RBI not used without permission

- decision_id: ADR-006
- date: 2026-10-03
- problem: Stage 10B adds regulator news. SEBI's feed (https://www.sebi.gov.in/sebirss.xml)
  holds only its latest 30 items - about three working days - so saving it by hand would miss
  releases. RBI's press-release and notification feeds exist, but RBI's website terms say
  "caching and links to, and the framing of this Web Site or any of the contents are
  prohibited", and linking to any page other than the home page needs RBI's written
  permission. RBI's server also refuses AI tools by name.
- options: (1) hand-save SEBI's feed; (2) let the program read SEBI's one feed address;
  (3) also read RBI's feeds; (4) ask RBI for written permission first.
- decision: (2), and RBI is not used. A narrow addition to ADR-005:
  - src/ingestion/news_fetch.py may also ask for exactly https://www.sebi.gov.in/sebirss.xml -
    no other address on SEBI's site, no redirects;
  - at most one read an hour (the feed's own time-to-live is 60 minutes); a sooner read is
    refused before anything is sent; one request per run, no retries;
  - every read that is used is kept byte for byte as a raw file before it is read;
  - releases are stored privately for research and never republished (SEBI's website policy
    allows linking without permission and asks for permission by email to reproduce);
  - no code names RBI's site; RBI can be added only after RBI gives written permission (a
    later decision).
  Enforced by tests: the fetcher refuses every other SEBI address, waits an hour between reads,
  and no module mentions RBI's site.
- reason: owner decision (2026-10-03) after reviewing SEBI's website policy, SEBI's robots.txt
  (allows all), RBI's terms and how RBI's server answers.
- impact: fetch-sebi reads the feed; run it at least daily or releases can be missed - a read
  that shares no release with the previous read says so. A release counts as public only from
  this system's first read of it (SEBI gives a date without a time). Titles sometimes name
  individuals and their tax ids: they stay in the private database and are never put in tests
  or the public repository.
- supersedes: none (adds to ADR-005)
- owner: project owner
