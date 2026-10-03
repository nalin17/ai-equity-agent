# HANDOFF - AI Self-Learning Equity Research Agent

Written 2026-10-02 at the end of a long build chat, so that a new chat can continue
without losing anything. Read this whole file before doing anything else.

State at handoff: Stage 9 committed as cf1c948, CI green, 393 tests passing,
database at schema version 14. Updated 2026-10-03 after Stage 10 (news from GDELT,
ADR-005) and Stage 10B (SEBI releases, ADR-006): 518 tests, schema version 16. The next
build is Stage 11 = architecture 40B step 10 (Sentiment Adapter). See section 9.

---

## 1. The person and how they work

- The owner (GitHub: nalin17) is NOT a developer. They follow step-by-step instructions
  exactly, paste code blocks into PowerShell, and reply "done". Explain in plain
  language; keep technical detail in the code, not in the chat.
- They want: lines of code and commands, built in stages, an acceptance record per
  stage in `stages/`, every stage committed and pushed to GitHub by them.
- When output is long they save it to a file (`test_output.txt`) for the assistant to
  read; the assistant reads project files directly from disk to verify.
- The owner delegates judgement: "whatever you feel is right and best suited to make
  the model robust". Prefer robustness and fail-closed behaviour over coverage.
- Never ask them to run PowerShell as Administrator (it once broke the pytest cache).
- They have a separate project (C:\Users\nalin\Documents\Stock-Analysis-Agent, repo
  nalin17/ai-self-learning-equity-research). Do NOT reuse it: ADR-002 (independent build).

## 2. Project facts

| Item | Value |
|---|---|
| Project folder | C:\Users\nalin\Projects\ai-equity-agent |
| GitHub | https://github.com/nalin17/ai-equity-agent (PUBLIC - never commit secrets or API keys) |
| OS / Python | Windows 11 Home, Python 3.14, venv at `.venv` (activate: `.venv\Scripts\Activate.ps1`) |
| Database | SQLite at `data/equity.sqlite` (ADR-001: DuckDB is blocked by Windows Smart App Control - never suggest disabling it) |
| Tests | pytest; `pytest.ini`: pythonpath = src, testpaths = tests, addopts = -p no:cacheprovider |
| CI | `.github/workflows/tests.yml`, Python 3.14, runs pytest on every push |
| Dependencies | requirements.txt: pytest, pyyaml (nothing else) |
| Internet use | only `fetch-news` (GDELT news, ADR-005) and `fetch-sebi` (SEBI's one RSS feed, ADR-006); everything else is hand downloads |
| Check CI | `curl -s "https://api.github.com/repos/nalin17/ai-equity-agent/actions/runs?per_page=1"` |

## 3. Authority documents

- `docs/Master_Architecture_v2_1_1_FROZEN.md` - THE frozen architecture. The owner said
  "consider this as final freezed architect, we will stick to it". Section numbers in
  code and acceptance records (4, 4A, 4C, 5B, 6C, 6D, 9B, 40B, 40D ...) refer to it.
- `docs/Master_Architecture_v1_11.md` - the original, kept for history.
- Decisions: `docs/decisions/ADR-001-sqlite.md`, `ADR-002-independent-build.md`,
  `ADR-003-etf-scope.md` (ETFs/mutual-fund units, ISIN prefix INF, are out of scope),
  `ADR-004-data-intake.md` (no scraping; hand downloads; licensed sources for scale),
  `ADR-005-news-from-gdelt.md` (news from GDELT, fetched by fetch-news - the only network code),
  `ADR-006-sebi-feed.md` (SEBI's RSS feed read hourly at most; RBI not used without permission).
- Scope (architecture section 3): one exchange (NSE, India), 30-company focus cohort
  first. Other countries' stocks need an architecture change request; global FX/rates
  are allowed only as macro context (the "Sector / macro" domain is Core).

## 4. Rules that must never be broken

1. NSE's Terms of Use (updated 29-Oct-2025) prohibit systematic or automated data
   collection. Do NOT build scrapers, do not bulk-download through the browser, do not
   use nsepython/jugaad-data or "NSE scraper" APIs. A static test
   (`tests/test_stage08c_intake.py::test_no_code_contacts_a_website`) fails if any
   module imports a network library. A licensed API would need a new ADR first. The
   exceptions: src/ingestion/news_fetch.py may call api.gdeltproject.org for news (ADR-005)
   and read https://www.sebi.gov.in/sebirss.xml at most hourly (ADR-006). RBI is not used:
   its terms forbid caching and linking without written permission.
2. TradingView data is display-only (non-display/machine use prohibited) - not a source.
3. The assistant never downloads files itself without explicit permission; reading a
   page in the browser to design code is fine. The owner downloads; the assistant reads
   files from `C:\Users\nalin\Downloads` or `data\inbox`.
4. Never ask for, display or store API keys/passwords in chat or in the repo.
5. Never repair source data silently; refuse, quarantine or mark missing with a reason.
6. Everything is append-only (triggers on history tables); corrections are new versions.
7. Point in time (5B): use only what was knowable at the decision time; publication
   times must be proven (exchange dissemination time) or the item is AVAILABILITY_REVIEW
   for historical replay.
8. Ingested text is data, never instruction (4D).

## 5. How each stage is built and handed over (follow exactly)

1. Research first on REAL data: read NSE pages in the browser (read only), then ask the
   owner to download specific files (give exact page, filters, file names). Inspect the
   real files before writing code (columns, quirks, identities).
2. Build in a scratch copy: `git ls-files | tar` into a scratchpad folder (t1..t15 were
   used), convert CRLF to LF there, run tests with
   `PYTHONPATH="src;../libs" python -m pytest -q` (pip libs were installed to a
   scratchpad `libs` folder; the venv is the owner's).
3. Run deliberate-fault checks: a small script mutates one line of the new module at a
   time and runs the stage tests; every fault must make a test fail (target 12/12).
   When a fault survives, add the missing test.
4. Run the real data on a COPY of the owner's database (`cp data/equity.sqlite`), with
   COPIES of their downloads (never touch their Downloads folder), and record the real
   numbers for the acceptance record.
5. Check every file to be pasted is pure ASCII and has no line starting with `'@`
   (that would end a PowerShell here-string).
6. Hand over as paste blocks:
   - New/whole files: `@' ... '@ | Set-Content -Encoding ascii path\file`.
   - Both migration files (up and down) in ONE block (the owner twice missed a down file).
   - Edits to existing files: a checked Python patch script piped as `@' ... '@ | python -`
     that normalises CRLF, checks every anchor occurs exactly once, writes with
     `newline="\r\n"`, prints `patched <file>` or `STOP: ... nothing was changed`.
     Test the patch on a copy of the owner's real file first, and check a second run STOPs.
   - Appending to `config/sources.yaml`: `@' ... '@ | Add-Content -Encoding ascii config\sources.yaml`
     (block starts with a blank line, two-space `- source_id:` indentation).
   - Then: run tests to `test_output.txt` and show the expected last line; `python manage.py init-db`
     with the expected version; the real-data commands with expected numbers; commit and push.
   - Commit messages end with `-m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`.
7. When the owner says "done": verify directly - `git log`, `tail -1 test_output.txt`,
   `diff -q --strip-trailing-cr` of every changed file against the tested copy, read-only
   DB queries (`sqlite3.connect("file:data/equity.sqlite?mode=ro", uri=True)`), and CI.
8. Tooling pitfalls learned: the Write tool turns a literal `\ufeff` into a real BOM and
   `\b` into a backspace - use `chr(0xFEFF)` in code; heredocs with backslashes are
   fragile - write scripts with the Write tool. Use `date.fromisoformat` ONLY in
   `core/dates.py` (`strict_iso_date`); a static test enforces it. Missing-data class
   names (e.g. "source_conflict") must not be written as string literals in `src/`
   outside `data_quality/missing_data.py` (static test). The bare token REVIEW is banned
   in `src/` (static test).

## 6. Stage history (all ACCEPTED, all pushed, CI green)

| Stage | Commit | Architecture | What it proved |
|---|---|---|---|
| 0-1 | 9773aa2, efd0c0b | setup | skeleton, settings, logging |
| 2 | 689c8e4 | 40B step 2 | SQLite migrations, source registry (ADR-001) |
| 3 | 88f045c | 4, 4C | ISIN identity, missing-data classes, excluded source classes, acceptance records, CI |
| 4 | 63a8cba | 4, 5B | trust chain, quarantine, raw artifact store, availability disposition (ADR-002) |
| 5 | 3f8761b | 40B step 4 | point-in-time fact store with versioned corrections |
| 6 | 2606dea | 40B step 5, 6A.1 | historical universe, survivorship; strict date parsing |
| 7A | 9aa2b52, 1eae6c1 | 40B step 6 | NSE bhavcopy adapters (legacy + UDiFF), equity list; ETFs out of scope (ADR-003) |
| 7B | e0386fb | 6C | corporate-action adjustment policy, raw vs adjusted series, fail-closed windows |
| 7C | c0c309a | 6C | NSE corporate actions reader, compare-series |
| 7D | b8db868 | 6D | identity bridges for ISIN changes at splits/bonuses |
| 8 | 535ae7e | 40B step 7 | old-format NSE results (CF-FR listing + INDAS XBRL): basis on every fact, FourD trap rejected, identities |
| 8B | d1ef32f | 40B step 7, 9B | SEBI integrated filings (Mar-2025 onwards) for Ind AS companies and banks; bank ratios standalone-only; ISIN check |
| 8C | 7e0b679 | ADR-004 | `checklist` page of links + `ingest-inbox` one-command loader; no network code |
| 8D | 7da4f0b | 40B step 7, 5 | NBFCs, life insurers, real 'Revision' rows, revisions recorded as dated corrections |
| 9 | cf1c948 | 40B step 8, 4A, 4D | NSE corporate announcements; one release = one event (rule an-dedup-1); subject->type mapping an-types-1 |
| 10 | see git log | 40B step 9, 4A, 4B.4, ADR-005 | news headlines from GDELT; extraction confidence stored apart from investment confidence; rules nw-entity-1 (company links) and nw-dedup-1 (copies) |
| 10B | see git log | 40B step 9, 4A, 5B, ADR-006 | SEBI releases from its RSS feed; public only from the first read; companies by exact registered name (sb-entity-1); kinds from SEBI's sections (sb-kinds-1) |

Acceptance records with exact claims, not-claimed items and negative assertions are in
`stages/STAGE_*_acceptance.yaml`.

## 7. Current state (verified at handoff)

- At Stage 9: 393 tests; schema version 14; 28 migration files. After Stage 10: 482 tests;
  schema version 15; 30 migration files (0001-0015 up/down). After Stage 10B: 518 tests;
  schema version 16; 32 migration files (0001-0016); news and SEBI counts: `python manage.py report`.
- Data loaded: 2,594 entities (EQUITY_L); 32 raw files; 13,806 trusted daily prices
  (6 bhavcopies, 20-Aug to 01-Oct-2026); 1,182 corporate actions; 1 identity bridge
  (TAALTECH); results listings 5 (old page) + 49 (integrated); 17 results files;
  751 fundamental figures (2 stored as missing); 5,903 announcement filings forming
  5,723 events.
- Companies with fundamentals: TCS, Reliance, VST Tillers (old format); HDFC Bank, TCS,
  Bajaj Finance, HDFC Life (integrated format).
- `data/inbox` holds 32 files (all ingested). The owner's Downloads may also hold
  unrelated files (ignore them).

## 8. Code map

- `manage.py` - commands: init-db, sources, load-equity-list, ingest-prices,
  load-corporate-actions, compare-series SYMBOL START END, bridge-isins,
  load-results-index FILE..., load-results FILE..., show-fundamentals SYMBOL [PERIOD_END],
  load-announcements FILE..., show-events SYMBOL [FROM] [TO],
  fetch-news [--symbols A,B] [--from DATE], show-news SYMBOL [FROM] [TO],
  fetch-sebi, show-sebi [--symbol SYMBOL] [FROM] [TO],
  ingest-inbox [--without-listing] [FOLDER], checklist [LISTING...] [--symbols A,B]
  [--since DATE] [--prices-from DATE], report.
- `src/core/` - config, database (`connect`, `migrate`, `rollback`, `run_in_transaction`,
  `now_utc`), dates (`strict_iso_date`), logging_setup, status (2A vocabulary,
  `load_acceptance_records`; status must be a fixed status or ACCEPTED_<X>_BASELINE).
- `src/data_quality/` - missing_data (`MissingClass`), trust_chain (`NoDataError` ...),
  extraction_confidence (`ExtractionConfidence`, 4A rule 4).
- `src/provenance/` - availability (`disposition(claim, decision_time, retrieved_at,
  published_at)`, `PitClaim.CURRENT_DECISION/HISTORICAL_REPLAY`, `Availability`),
  raw_store (`store_raw_artifact`, sha256 dedup), pit_store (`record_fact`,
  `record_correction`, `fact_as_of`; UNITS include INR, INR_per_share, ratio).
- `src/universe/` - entities (`resolve(conn, symbol, as_of, alias_type="nse_symbol")`),
  equity_list, historical_universe, identity_bridges.
- `src/ingestion/` - source_registry, market_adapters (`read_raw_table`, providers,
  `ingest_market_file`, `retry_quarantined`), corporate_actions + nse_corporate_actions
  (`normalise_name`), nse_financial_results (all results formats: OLD_INDAS and
  SEBI_FORMATS IndAS/Banking/NBFC/LI, listings, identities, standalone-only ratios,
  revisions), intake (checklist + ingest-inbox), nse_announcements (filings, `events()`),
  gdelt_news (GDELT articles, news names, `extract()`, `stories()`), news_fetch (the only
  network code: GDELT requests, spacing, back-off, window splitting; SEBI's feed, hourly),
  sebi_releases (SEBI feed reads, `releases()`, rules sb-kinds-1 and sb-entity-1).
- `src/features/price_series.py` - raw/adjusted series.
- Empty packages reserved for later steps: abstention, calibration, experiments, ledger,
  models, regimes, research, targets, validation.

## 9. Architecture roadmap (40B) and the next step

Done: steps 1-9. Our stage numbers: step 6 = Stage 7, step 7 = Stage 8/8B/8D,
step 8 = Stage 9, step 9 = Stage 10/10B. 8C was the intake tooling.

NEXT: Stage 11 = 40B step 10, Sentiment Adapter.
Acceptance (40B): "Features below the liquidity threshold are refused, not down-weighted
(4B.2)". Read 4B (4B.1-4B.5), 4C, 4E, 5B and 14.0 (investability) before designing.
Sentiment may use only sentiment-eligible stories (4B.4): Stage 10's 'subject' articles;
'mentioned' and search-only stories feed attention only. GDELT also offers tone - a model
output: keep it, never flip it (4B.5). The liquidity threshold needs traded value from
trusted_prices. Stage 10B (SEBI releases) is done; RBI waits for written permission.

Then: step 11 Knowledge/Event Hub (one point-in-time evidence object), 12 Real Feature Factory,
13 Real Target Engine, 14 Equity Research Agent v0.1 (first agent), 15 Prediction
Ledger, 16 Shadow operation, 17-23 resolver, attribution, calibration, drift,
controlled learning, specialist agents, API.

## 10. NSE real-data findings (the code depends on these)

Prices / identity:
- ETFs trade in series EQ with ISIN prefix INF (out of scope, ADR-003).
- ISIN changes at splits (TAALTECH INE524T01011 -> INE524T01029 on 22-Sep-2026);
  bridged by Stage 7D. FACE VALUE in corporate actions shows the new value after the ex-date.
- Bhavcopy archive link: https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip
Results (old page, periods to Dec-2024): CF-FR listing; INDAS_*.xml in BSE taxonomy;
- the 'FourD' context claims the quarter but holds year-to-date figures - rejected;
- VST Tillers had placeholder zeros for owners/minority profit - stored as source_conflict.
Results (Integrated Filing - Financials, quarters ended Mar-2025 onwards, SEBI format):
- listing CSV header cells end with a space and a line break (stripped by read_raw_table);
- files carry Symbol and ISIN; family is in the in-capmkt-ent namespace
  (IntegratedFinance_IndAS / Banking / NBFC / LI); taxonomy date varies (2025-01-31, 2026-01-31);
- bank and insurer consolidated reports carry zeros or copies for regulatory ratios
  (NPA, CET1, ROA; solvency, persistency) - taken from standalone only;
- March files say both Audited (year) and Unaudited (quarter);
- a revision row: TYPE OF SUBMISSION "Revision", BROADCAST blank, REVISED DATE/TIME
  like "24-JUL-2026 16:48:18", REVISION REMARKS text, dissemination = when the revised
  file went public (HDFC Life, 24-Jul-2026; its P&L figures equal the original).
- General insurers and other families are refused until checked on real files.
Announcements (CF-AN-equities-*.csv): columns SYMBOL, COMPANY NAME, SUBJECT, DETAILS,
BROADCAST DATE/TIME, RECEIPT, DISSEMINATION, DIFFERENCE, ATTACHMENT (no ISIN, no size);
- attachment link = corporate/UPLOADER_ddmmyyyyhhmmss_originalname;
- companies file one document several times under different subjects within minutes
  (HDFC Bank 18-Apr-2026, four filings); generic names (intimation.pdf, a bare symbol)
  and even specific names are reused for different documents days later;
- the per-announcement XBRL only repeats the listing fields.

News (GDELT DOC 2.0 API, article list, JSON; checked 02-Oct-2026):
- fields: url, url_mobile, title, seendate (UTC, always on 15-minute marks), socialimage,
  domain, language, sourcecountry; the search text is NOT in the response (the fetcher
  records it); at most 250 articles per response; only the last 3 months are searched;
- headlines arrive tokenised ('66 % returns , small - cap'); English, Hindi, Marathi and
  Gujarati - other scripts must keep their letters when headlines are compared;
- a company search returns mostly other stories (HDFC Bank, 1 week: 138 articles, 13
  stories about the bank); lists of stocks are common - hence rule nw-entity-1;
- copies: wire stories on two sites, one site's story in two sections, print and web
  editions, a tips site republishing one article under ~10 addresses over 33 hours;
- refusals: HTTP 429 'Please limit requests to one every 5 seconds', in waves - even 8
  seconds after a success; on 03-Oct-2026, after a night of testing, for hours (the
  fetcher then gives up for the run and stores nothing); also network drop-outs;
- Business Standard and HT/Mint terms forbid AI use of their content: never open links.

SEBI releases (https://www.sebi.gov.in/sebirss.xml; checked 03-Oct-2026):
- RSS 2.0, ttl 60; only the latest 30 items (about three working days); each item has title,
  description (same as the title), link and pubDate as a date only ('01 Oct, 2026 +0530');
  no guid; links look like /enforcement/orders/oct-2026/<slug>_<id>.html;
- sections seen: enforcement/orders, enforcement/recovery-proceedings, legal/circulars,
  media-and-notifications/press-releases; titles may contain curly quotes;
- titles name companies by registered name ('... in the matter of SMC Global Securities Ltd'),
  groups ('Adani Group Companies'), near misses ('Lloyd Enterprises Limited' vs the listed
  'Lloyds Enterprises Limited') and individuals with tax ids - keep those out of tests;
- RBI: website terms forbid caching and linking without permission; its server refuses AI tools.

## 11. Open items, deferred work and things NOT claimed

- Rows refused by an earlier code version cannot be re-read from a stored listing
  (a later fix needs a re-download with new bytes). Consider a reprocess tool.
- Per-share figures are not adjusted for bonuses/splits; balance sheet and cash flow
  not stored; segment results not stored; half-year/nine-month periods not stored.
- NBFC GS3/AUM and insurer VNB/APE are not in the XBRL files.
- Announcements: duplicates judged by file name and timing, not PDF bytes; direction,
  materiality and horizon not assessed; unclassified subjects not read from text;
  no BSE cross-exchange syndication.
- 125 announcement rows (52 symbols) were refused: companies not in EQUITY_L.
- News (Stage 10): headlines only, article text never read; event type, direction,
  materiality and horizon not assessed; news repeating an exchange filing not recognised;
  short forms ('Reliance', 'TCS', 'HDFC') and names only in other scripts not matched;
  'sources say' stories not screened (4F.2); site quality not assessed; extraction runs not
  filtered by decision time; only 6 companies have news names (config/news_names.yaml).
- SEBI (Stage 10B): titles only; releases before the first read are missing; whether a named
  company is the party acted against is not assessed; circulars not linked to sectors; no RBI.

## 12. Data-source research already done (do not repeat)

- NSE Terms of Use forbid automated collection (checked 2026-10-02). robots.txt allows
  crawling but the terms bind the user.
- Free official route for history: SEBI circular of 20-Dec-2024 - exchanges share data
  for research (up to 2 GB/researcher/year free; academic, non-commercial) via a request
  form to nseri@nse.co.in (BSE has its own form). The assistant offered to draft it.
- NSE paid: EOD Corporate Announcement product Rs 5,00,000/yr (SFTP); real-time
  corporate data Rs 10,60,000/yr.
- Broker APIs: Zerodha staff say Kite Connect is "purely an execution platform" and
  point data users to authorised vendors; static-IP whitelisting applies only to order
  APIs. Groww API (Rs 499/month) history only from 2020, adjustment unclear. Fyers and
  Upstox advertise free history; Dhan Rs 499/month.
- Authorised Indian vendors: TrueData (has a Corporate & Fundamental Data API - ask for
  a quote and whether it gives basis and dissemination times), Global Datafeeds,
  Accord Fintech (ACE Equity). Trendlyne Rs 299/month AI-tool plan has too few calls.
- Global (only if scope changes): Twelve Data Pro (~$229/month, verified on its exchange
  list: NSE/BSE, US, Tokyo, Shanghai/Shenzhen, forex, fundamentals; personal use);
  FMP Ultimate (~$99/month annual; India/Japan/China coverage not confirmed); EODHD
  does NOT list Indian or Tokyo exchanges and says its prices are indicative.
  Official free sources: SEC EDGAR (US), J-Quants (Japan, by JPX), filings.xbrl.org
  (Europe annual), ECB and FRED (FX/macro).
- Recommendation given: stay with hand downloads + checklist for the 30-company cohort;
  NSE research request for history; authorised vendor quote for scale later.
- News (checked 02/03-Oct-2026): Business Standard's terms forbid automated collection,
  caching and any AI use (grounding/RAG included); HT Digital (HT, Mint) forbids AI/ML use
  without a written licence (RSS included); Economic Times blocks automated reading.
  GDELT: open data, 'unlimited and unrestricted use', cite gdeltproject.org - chosen
  (ADR-005). Paid news APIs, terms on storage and AI use NOT yet checked: Marketaux from
  $29/month, NewsData.io from ~$200/month, NewsAPI.org $449/month (free plan for testing
  only). Regulators: PIB allows reuse with acknowledgement; RBI's website terms forbid
  caching and linking without written permission (checked 03-Oct-2026); SEBI allows
  linking and asks for an email before republishing - its feed is read (ADR-006).

## 13. How to start the new chat

Paste this to the new chat:

> I am continuing my AI equity research agent project at
> C:\Users\nalin\Projects\ai-equity-agent. Please read docs/HANDOFF.md fully first,
> then the frozen architecture docs/Master_Architecture_v2_1_1_FROZEN.md sections
> named there. Verify the current state (git log, tests, database version 15, CI), then
> continue with Stage 11 (architecture 40B step 10, Sentiment Adapter) using the
> same step-by-step method: research real data first, build and test in a scratch copy,
> give me paste blocks and commands, and verify after I reply "done".
