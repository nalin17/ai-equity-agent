# ADR-013 - GDELT GKG headlines and company sentiment from filings and headlines (Stage 12A)

- decision_id: ADR-013
- date: 2026-11-22
- problem: 40B step 10 (Sentiment Adapter, architecture 4B, 9A). The news route of Stage 10 is blocked: GDELT's
  DOC API has answered HTTP 429 to the owner's computer since 05-Oct-2026 on broadband and phone hotspot, so no
  news is stored. Alpha Vantage NEWS_SENTIMENT is premium-only (05-Nov); Marketaux scores sentences VADER-style,
  mostly market round-ups; EODHD has no NSE news; publisher RSS feeds need written permission (asked 09-Nov).
  GKG's tone is whole-article, so one story about five companies would give all five the same score.
- options: (1) GDELT's bulk GKG 2.1 files on data.gdeltproject.org - same open licence as the DOC API, every row
  has the page title, files can be read for past weeks; about 0.4 GB a day; (2) a paid vendor's per-company
  score - black boxes, may be recomputed, India coverage unverified; (3) wait for permissions.
- decision: (1), approved by the owner on 09-Nov-2026 ("company sentiment from filings plus news headlines"), with
  the owner's choices of 22-Nov-2026: FinBERT as the headline scorer (Stage 12B, its own ADR), a liquidity band
  of Rs 25 crore a day, calendars regenerated in December. Stage 12A builds everything except the scorer:
  - New host data.gdeltproject.org in news_fetch.ALLOWED_HOSTS; only /gdeltv2/lastupdate.txt and
    /gdeltv2/<YYYYMMDDHHMMSS>.gkg.csv.zip, over https with certificates checked (GDELT lists http addresses,
    which only redirect; redirects stay refused). Requests 2 seconds apart; any answer other than 200 or 404
    stops the run. A slot is asked for only when at least 75 minutes old: Google's cache keeps an empty 404 for
    up to an hour for a file asked for before upload (measured 05-Nov), so a 404 is 'not yet', never 'no news'.
    fetch-gkg reads the last day on its first run, later the unread slots of the last week (at most 96 files a
    run by default); --from reads further back.
  - A file is used whole or not at all: one zip member <slot>.gkg.csv, UTF-8, 27 fields in every row, every
    row's DATE equal to the slot; GDELT's md5 checked when lastupdate.txt lists the file. The raw file is NOT
    kept (0.4 GB a day): gk_files records its name, size, md5, sha256 and retrieval. Only India-relevant rows
    are stored (rule gk-keep-1: located in India, from an Indian outlet, or a declared news name in the headline):
    link, page title verbatim, site, GDELT's time, the page's own stated time (a claim, never proof), and
    V1.5TONE. A link is stored once; the same link with another headline later is a recorded conflict.
  - Availability (5B): GDELT's slot + 15 minutes, or our retrieval if earlier - the DOC API's rule.
  - Attribution is Stage 10's rule nw-entity-1, unchanged: subject only when a declared news name is in the
    headline and the link, alone, not a list item; the body is never read (an Infosys 'mention' in the samples
    was a US politics story). One story is one vote: Stage 10's nw-dedup-1, unchanged.
  - Fixed, versioned rules in src/knowledge/sentiment.py, written before any outcome is seen: an-direction-1
    (a filing's direction from NSE's subject alone - NSE's details text is boilerplate, so a rating's or an
    auditor change's direction is only in the PDF and stays 'unknown'; opposite subjects are 'conflicting', never
    netted); se-echo-1 (round-ups, gainers and losers, tips, 52-week and circuit headlines, a stock's own move -
    price echo, attention only); se-eligible-1 (subject and not price echo); se-liquidity-1 (median close x
    volume over the last stored sessions known at the decision, none older than 120 days, at least Rs 25 crore
    from at least 5 sessions;
    below, refused - never down-weighted, 4B.2 rule 1).
  - The hub (hub-2) gives GKG stories as news (attention-eligible, with their eligibility and GDELT's article tone
    labelled as whole-article) and, for public sentiment, the filings with a direction and the eligible headlines
    - unscored. Public sentiment leaves NOT_BUILT. Gaps say: refused by the band, filings without a readable
    direction, ineligible headlines, no evidence at all ('never neutral'), polarity not scored yet (12B), sentiment
    features not computed, and the window's GKG slots not read.
- consequences: no stored text is about a company unless its headline names it; the owner's 6 declared news names
  limit attribution until more are declared in config/news_names.yaml. GDELT's tone is never company sentiment.
  The DOC API code stays (it may answer again). Under historical replay sentiment is refused until prices have a
  proven publication time. About 0.4 GB a day is downloaded; little is stored.
- not decided here: the scorer (Stage 12B: FinBERT, CC BY-NC-SA 4.0, weights downloaded by hand, pinned by hash,
  never in the repo); BusinessLine/The Hindu and RBI RSS (next stage, own ADRs); NSE PIT/SAST/pledge CSVs.
- licence: GDELT open data - every use cites the GDELT Project (https://www.gdeltproject.org/); article links are
  never opened (ADR-005).
