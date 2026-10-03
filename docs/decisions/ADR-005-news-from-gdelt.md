# ADR-005 - News from GDELT, fetched by the program; no other automated collection

- decision_id: ADR-005
- date: 2026-10-03
- problem: Stage 10 (architecture 40B step 9) needs news. Commercial Indian news sites do
  not allow it: Business Standard's terms forbid automated collection, caching and any use
  of their content in an AI system, naming grounding and retrieval-augmented generation;
  HT Digital (Hindustan Times, Mint) forbids AI and machine-learning use without a written
  licence, RSS feeds included; Economic Times refuses automated reading. Hand-downloading
  news every day does not scale, and the owner asked for an API.
- options: (1) hand-save GDELT search results in the browser; (2) let the program call
  GDELT's DOC 2.0 API, whose terms allow any use including automated, with citation;
  (3) a paid news API (Marketaux from about $29/month, NewsData.io from about $200/month,
  NewsAPI.org $449/month) - terms on storing articles and AI use not yet checked;
  (4) publishers' RSS feeds - their terms forbid this use.
- decision: (2). A narrow exception to ADR-004:
  - only src/ingestion/news_fetch.py may open a network connection, and only to the hosts
    in its ALLOWED_HOSTS (api.gdeltproject.org); redirects are never followed;
  - at least 20 seconds between requests; after a refusal (HTTP 429 or GDELT's 'Please
    limit requests' notice) it waits 1, 3 and 5 minutes, then gives up, stores nothing and
    asks GDELT nothing more in that run;
  - every response that is used is kept byte for byte as a raw file before it is read;
  - article links are never opened and article text is never read - only the headline,
    link, site, language, country and the time GDELT first saw each article;
  - NSE data is never fetched; ADR-004 stands for everything else.
  Enforced by static tests: no other module imports a network library, the fetcher names
  no other host, and no module in src imports the fetcher.
- reason: owner decision (2026-10-03) after reviewing the publishers' terms and GDELT's.
  GDELT's terms: "unlimited and unrestricted use for any academic, commercial, or
  governmental use of any kind without fee", citing the GDELT Project with a link to
  https://www.gdeltproject.org/ - recorded in the source registry. The headlines are the
  publishers' words as GDELT recorded them; they are used as data for this private
  research database and are not republished.
- impact: fetch-news is the only command that uses the internet. GDELT's DOC API searches
  only the last 3 months, so history older than that needs GDELT's bulk files or BigQuery
  (a later decision). GDELT refuses requests in waves (seen 02-Oct-2026: refusals 8 seconds
  after a success; on 03-Oct-2026, after a night of testing, refusals for hours), so a fetch
  can take minutes and may need repeating later; a refused company is reported, never stored
  as 'no news'. If refusals persist for days, GDELT's raw 15-minute files are the fallback
  (a later decision). Any output published from this project must cite GDELT.
- supersedes: none (amends ADR-004 for news from GDELT only)
- owner: project owner
