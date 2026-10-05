# ADR-011 - Aggregate investor flows from NSE's daily FII/DII files, downloaded by hand

- decision_id: ADR-011
- date: 2026-10-04
- problem: Stage 10E (architecture 40B step 9c, 3C, 3G) needs daily FPI/FII and DII flows - the main
  channel through which global events reach Indian prices - stamped with their publication time, never
  their trade date (3C rule 1).
- research (2026-10-04; read in the owner's Chrome, read only; nothing downloaded by the assistant):
  - NSDL's FPI Monitor (fpi.nsdl.co.in) publishes the official daily FPI figures, but its disclaimer says
    that reproduction, redistribution and transmission of any information on the site are strictly
    prohibited. Its servers also reset connections from non-browser clients on the owner's computer.
  - CDSL's FPI page carries the same report set; its copyright policy forbids copying, downloading or
    storing the content of its pages in any medium without CDSL's prior written permission.
  - NSE's page 'FII/FPI & DII trading activity' (nseindia.com/reports/fii-dii) shows only the latest trading
    day, for NSE and for NSE, BSE and MSEI combined, each with a CSV download. NSE calls the figures
    provisional (FII/FPI compiled from PANs provided by NSDL; DII from members' trading codes) and points to
    NSDL and CDSL for final data. NSE's terms forbid automated collection, so files are downloaded by hand,
    as bhavcopies are (ADR-004).
  - Real files (01-Oct-2026, downloaded 04-Oct-2026): fii-dii-nse-latest.csv and
    fii-dii-combined-latest.csv - names without a date; a byte-order mark; header cells split over two lines
    with the rupee sign; two rows (DII, FII/FPI); amounts with thousands commas; net = buy - sell.
- options: (1) NSDL or CDSL figures as published - not allowed by their terms; (2) NSE's provisional CSV by
  hand; (3) wait for written permission or for NSE's research data; (4) defer.
- decision: (2) now, and the owner asks NSDL for written permission (email drafted in
  data/handover/nsdl_request/email_to_nsdl.txt, sent by the owner) - approved by the owner on 2026-10-04
  ("Both: NSE CSV by hand + ask NSDL"):
  - no new network access: the owner downloads the two CSVs each trading evening; ingest-inbox moves them
    from the Downloads folder (a repeated name is kept under a content tag) and loads them;
  - the header must be exactly the declared five columns in crore; both categories once, one trade date,
    buy and sell not negative, net equal to buy minus sell to the paisa; the trade date an NSE trading day
    (XBOM calendar) not after ingestion - anything else refuses the file whole, nothing repaired;
  - a value is known from this system's ingestion of the file - never its trade date; historical replay
    stays in AVAILABILITY_REVIEW (NSE gives no publication time); a day read again with other figures is a
    new vintage;
  - trading days without a file are reported as missing (extraction failure) and never filled;
  - flows are context only (3G rule 2): never a covered security, target or benchmark.
- reason: the only free source whose terms allow this personal use; official exchange figures with the same
  compilation as NSDL's provisional data; fail-closed checks on a format with real quirks.
- impact: one hand download of two small files each trading evening. Not covered: final NSDL/CDSL figures
  (until permission), days not downloaded on the day (history only through NSE's research request), F&O
  segment flows, the publication time of each day's figures.
- supersedes: none (adds to ADR-004)
- owner: project owner
