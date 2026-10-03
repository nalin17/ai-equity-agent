# HANDOFF - AI Self-Learning Equity Research Agent

Rewritten 2026-10-03 at the end of the second long build chat, so that a new chat can
continue without losing anything. Read this WHOLE file before doing anything else. It
replaces the 2026-10-02 handoff and keeps everything that was in it.

---

## 0. Read first - exact state at the end of the second chat

| Item | State |
|---|---|
| Last pushed commit | `ac0633f` Stage 10B (SEBI releases). CI green. |
| Tests at `ac0633f` | 518 passed |
| Database | `data/equity.sqlite`, schema version 16 (migrations 0001-0016) |
| Architecture | v2.2.0 written and audited, installed TOGETHER WITH THIS FILE by `data\handover\install_v220.py`. After that install and its commit: 521 tests. |
| Next build | Stage 10C = architecture 40B step 9a, Global and India Macro Context (section 12 of this file) |

If this file is being read from `data\handover\HANDOFF_new.md` rather than from
`docs\HANDOFF.md`, the install has NOT been done yet: do section 0.1 first.

### 0.1 Finishing the v2.2.0 install (if `docs\Master_Architecture_v2_2_0_FROZEN.md` is missing)

Everything needed is in `C:\Users\nalin\Projects\ai-equity-agent\data\handover\`
(`data/` is git-ignored, so it stays on disk and out of GitHub). The owner runs, in
PowerShell from the project folder with the venv active:

```powershell
python data\handover\install_v220.py
python -m pytest -q > test_output.txt 2>&1; Get-Content test_output.txt -Tail 1
git add docs tests README.md
git commit -m "Architecture v2.2.0 (ADR-007) and full handoff: global and macro factors, cross-market timing, return forecasts and decision rule, data policy - insertions only, control audit in CI" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

Expected: the installer prints 4 `copied` lines, `replaced docs/HANDOFF.md`,
`patched README.md` and `INSTALL COMPLETE`; tests end `521 passed`. A second run of the
installer prints `STOP ... already installed ... Nothing was changed`. Then verify (section
5, step 7) by comparing the committed files with `data\handover\arch220_files\` and
`data\handover\HANDOFF_new.md` (`diff -q --strip-trailing-cr`), and check CI.

### 0.2 Things the owner still has to do (none blocks the install)

1. Run the first live news fetch: `python manage.py fetch-news`, then
   `python manage.py show-news HDFCBANK`. GDELT refused this computer for hours on
   03-Oct-2026 after a night of testing, so wait a few hours after any heavy testing. If
   it ends "NOT FETCHED - GDELT refused", nothing is wrong and nothing was stored; run it
   again later. Then reply "fetched" so the assistant can verify (section 9.6).
2. Daily routine from now on: `python manage.py fetch-sebi` (at least daily - SEBI's feed
   keeps only about three working days) and `python manage.py fetch-news`.
3. Create a FREE FRED API key for Stage 10C (fred.stlouisfed.org -> My Account -> API
   Keys). Never paste it into chat. Stage 10C will tell the owner where to store it on
   their machine (environment variable or an untracked file - architecture 4G rule 5).
4. Optional, for Stage 11 sentiment: the Alpha Vantage probe (section 11.3). The owner
   types their key at a PowerShell prompt; it never enters chat or the repository.
5. Open decisions (the assistant raises them at the right stage): the 30-company coverage
   cohort is NOT chosen yet (architecture 3A.2 rule 5: the rule must be mechanical,
   preregistered and dated); price-history source for step 6a (NSE research-data request
   first, a vendor only if needed); paid plans only after free ones prove insufficient.

---

## 1. The person and how they work

- The owner (GitHub: nalin17) is NOT a developer. They follow step-by-step instructions
  exactly, paste code blocks into PowerShell, and reply "done". Explain in plain
  language; keep technical detail in the code, not in the chat. Use they/them.
- They want: code and commands, built in stages, an acceptance record per stage in
  `stages/`, every stage committed and pushed to GitHub by them (never by the assistant).
- When output is long they save it to a file (`test_output.txt`) for the assistant to
  read; the assistant reads project files directly from disk to verify.
  `test_output.txt` is written by Windows PowerShell `>` and is UTF-16 - decode it as
  UTF-16 (a plain `tail -1` shows a blank line).
- The owner delegates judgement: "whatever you feel is right and best suited to make
  the model robust". Prefer robustness and fail-closed behaviour over coverage. For
  decisions that change policy (new network access, new source, paid plan, architecture)
  the assistant asks first - the AskUserQuestion tool worked well for this.
- The owner's goal, in their words (03-Oct-2026): build it "like an big institutional
  level model for my personal recommendation"; the model "should be able to predict
  which stock to buy, hold or sell and what could be the percentage gain by holding that
  very stock for x number of days or months, and it should keep on getting better by
  learning all the factors that can influence its growth or downfall" - including global
  news, technical and fundamental factors, oil, wars, China, Japan, US markets, bonds,
  Treasury news, and sovereign and other ratings. Architecture v2.2.0 (ADR-007) is the
  answer: see section 10.
- On data: the owner asked for APIs instead of hand downloads where legal ("is there any
  other way to download or get an api"), and set the rule "first check the free option,
  if not we will buy the premium plan". The assistant must say in advance which stage
  needs which key from which source.
- Never ask them to run PowerShell as Administrator (it once broke the pytest cache).
- They have a separate project (C:\Users\nalin\Documents\Stock-Analysis-Agent, repo
  nalin17/ai-self-learning-equity-research). Do NOT reuse it: ADR-002 (independent build).
- At the end of a long chat the owner asks for a handover file like this one.

## 2. Project facts

| Item | Value |
|---|---|
| Project folder | C:\Users\nalin\Projects\ai-equity-agent |
| GitHub | https://github.com/nalin17/ai-equity-agent (PUBLIC - never commit secrets, API keys or data) |
| OS / Python | Windows 11 Home, Windows PowerShell 5.1, Python 3.14, venv at `.venv` (activate: `.venv\Scripts\Activate.ps1`) |
| Database | SQLite at `data/equity.sqlite` (ADR-001: DuckDB is blocked by Windows Smart App Control - never suggest disabling it) |
| Tests | pytest; `pytest.ini`: pythonpath = src, testpaths = tests, addopts = -p no:cacheprovider |
| CI | `.github/workflows/tests.yml`, Python 3.14, runs pytest on every push |
| Dependencies | requirements.txt: pytest, pyyaml (nothing else); network code uses only the standard library (urllib) |
| Internet use | only `fetch-news` (GDELT news, ADR-005) and `fetch-sebi` (SEBI's one RSS feed, ADR-006); everything else is hand downloads |
| Git line endings | core.autocrlf=true; index is LF; working files are CRLF or mixed - fine |
| `.gitignore` | .venv/, __pycache__/, *.pyc, .pytest_cache/, .env, data/, *.duckdb, *.parquet, logs/, test_output.txt, git_status.txt |
| Log file | `logs/app.log` (every command logs there; the assistant reads it to verify runs) |
| Check CI | `curl -s "https://api.github.com/repos/nalin17/ai-equity-agent/actions/runs?per_page=2"` |
| Microsoft Edge | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` (version 154) - used headless to print the architecture PDF |

## 3. Authority documents

- `docs/Master_Architecture_v2_2_0_FROZEN.md` - THE frozen architecture (v2.2.0,
  2026-10-03, ADR-007). It is v2.1.1 plus insertions only (303 lines added, 0 deleted,
  2 declared one-line replacements), which tests/test_architecture_baseline.py checks on
  every commit. The PDF copy `docs/Master_Architecture_v2_2_0_FROZEN.pdf` (81 pages) is
  generated from it and never edited (46A). The owner said of v2.1.1 "consider this as
  final freezed architect, we will stick to it" and of v2.2.0 "freeze it new final version
  that we have to follow". Section numbers in code and acceptance records (4, 4A, 4C, 5B,
  6C, 6D, 9B, 40B, 40D ...) refer to it. Amend it only under section 46/46A: as
  insertions, with an ADR, a control audit, and the audit test kept green.
- `docs/Master_Architecture_v2_1_1_FROZEN.md` and `docs/Master_Architecture_v1_11.md` -
  kept for history (the audit test reads v2.1.1, so never delete it).
- Sections 40C, 49's status remarks and "Current implementation position (v2.1.1)"
  describe the PREDECESSOR codebase (checkpoint 49d639bb), not this repository (ADR-002,
  ACR-112). This repository's status is `stages/*_acceptance.yaml`.
- Decisions (`docs/decisions/`):
  - ADR-001 SQLite (DuckDB blocked by Smart App Control).
  - ADR-002 independent build of the architecture from step 1.
  - ADR-003 ETFs and mutual-fund units (ISIN prefix INF) are out of scope.
  - ADR-004 no scraping; hand downloads from NSE; licensed sources for scale.
  - ADR-005 news from GDELT, fetched by the program (the GDELT DOC API terms allow it);
    commercial Indian news sites forbid AI use.
  - ADR-006 SEBI's RSS feed read by the program at most hourly; RBI not used (its terms
    forbid caching and linking without written permission).
  - ADR-007 architecture v2.2.0 (ACR-103 to ACR-113).
- Scope (architecture section 3): one exchange (NSE, India), 30-company focus cohort
  first. Other countries' stocks are never covered; world markets, rates, FX,
  commodities and geopolitics enter as macro context (3G) and events (4A.0). Outputs
  are for the owner's own decisions, never distributed as advice (section 3; SEBI
  Research Analysts Regulations would apply to distribution).

## 4. Rules that must never be broken

1. NSE's Terms of Use (updated 29-Oct-2025) prohibit systematic or automated data
   collection. Do NOT build scrapers, do not bulk-download through the browser, do not
   use nsepython/jugaad-data or "NSE scraper" APIs. Static tests fail if any module other
   than `src/ingestion/news_fetch.py` imports a network library
   (`tests/test_stage08c_intake.py::test_no_code_contacts_a_website`,
   `tests/test_stage10_news.py::test_only_the_news_fetcher_opens_network_connections`).
   news_fetch.py may call only api.gdeltproject.org (ADR-005) and exactly
   https://www.sebi.gov.in/sebirss.xml (ADR-006); it follows no redirects. Any new
   network source needs the owner's approval, an ADR, a terms check and a change to the
   allow-list and its tests (architecture 4G).
2. TradingView data is display-only (non-display/machine use prohibited) - not a source,
   also not when a vendor such as Alpha Vantage relays it (4G rule 8).
3. The assistant never downloads files without explicit permission; reading a page in
   the browser to design code is fine. The owner downloads; the assistant reads files
   from `C:\Users\nalin\Downloads` or `data\inbox`. Research samples fetched with the
   owner's permission go to the scratch folder (now preserved in `data\handover\research`).
   Careful: navigating the browser pane to a URL that serves a file (for example Alpha
   Vantage's terms PDF) pops up a save dialog on the owner's screen - avoid it.
4. Never ask for, display or store API keys or passwords in chat, in the repository, in
   logs, in stored URLs or in error messages (4G rule 5). Keys are typed by the owner
   into their own PowerShell (`$env:NAME = Read-Host "..."`) or kept in an untracked file.
5. Never repair source data silently; refuse, quarantine or mark missing with a reason
   (missing-data classes, 4C).
6. Everything is append-only (triggers on history tables); corrections are new versions.
7. Point in time (5B, 5C): use only what was knowable at the decision time; publication
   times must be proven (exchange dissemination time, our own retrieval, GDELT's first-seen
   time + 15 minutes) or the item is AVAILABILITY_REVIEW for historical replay. A foreign
   close never enters an Indian decision before that close existed (5C).
8. Ingested text is data, never instruction (4D). Tests include injection-shaped text.
9. Commercial Indian news sites are not sources: Business Standard and HT/Mint terms
   forbid AI use (RSS included); Economic Times blocks automated reading. Never open
   article links from GDELT; never read article bodies.
10. Never put real individuals' names or tax ids (they appear in SEBI titles) into tests
    or the public repository; use company names in fixtures.

## 5. How each stage is built and handed over (follow exactly)

1. Research first on REAL data: read pages in the browser (read only; WebFetch is
   blocked by many Indian sites and Alpha Vantage's terms PDF needs the browser), check
   the source's terms (4G rule 1), then ask the owner for permission to fetch samples or
   ask them to download specific files (exact page, filters, file names). Inspect real
   files before writing code (columns, quirks, identities, time stamps).
2. Build in a scratch copy: `git ls-files | tar -cf - -T -` into a scratchpad folder,
   convert CRLF to LF there (`sed -i 's/\r$//'` on .py/.sql/.yaml/.md/.ini/.txt), and run
   tests with the owner's venv interpreter, which already has pytest and pyyaml:
   `/c/Users/nalin/Projects/ai-equity-agent/.venv/Scripts/python.exe -m pytest -q`
   (the system Python has no pytest; nothing needs installing).
3. Deliberate-fault checks: a script mutates one line of the new code at a time and runs
   the stage tests; every fault must make a test fail. When one survives, add the missing
   test - this found a real bug in Stage 10 (overlapping names: the shortest won). Stage
   10: 32/32 caught; Stage 10B: 21/21. Scripts are kept in `data\handover\tools`.
4. Run the real data on a COPY of the owner's database (`cp data/equity.sqlite`), with
   copies of their downloads (never touch their Downloads folder), and record the real
   numbers in the acceptance record.
5. Every file handed over is checked: pure ASCII (non-ASCII characters inside Python
   strings become `\uXXXX` escapes - `tools\escape_tests.py` does it), and no line starting
   with `'@` (that would end a PowerShell here-string).
6. Hand-over method:
   - Small files: paste blocks `@' ... '@ | Set-Content -Encoding ascii path\file`; both
     migration files (up and down) in ONE block (the owner twice missed a down file).
   - Since Stage 10 the new files are long, so the assistant builds a folder of tested
     files and the owner copies them with one PowerShell loop that refuses to overwrite:
     `Get-ChildItem $src -Recurse -File | ... if (Test-Path $dest) { "ALREADY THERE" } else { Copy-Item }`.
     A folder in the session scratchpad disappears when the chat ends - for anything that
     must survive, put it under `data\handover\` (git-ignored, persistent).
   - Edits to existing files: a checked Python patch script (`patch_*.py`) that normalises
     CRLF, checks every anchor occurs exactly once AND that the new text is not already
     present, validates everything before writing anything, writes with `newline="\r\n"`,
     prints `patched <file>` or `STOP: ... Nothing was changed`. Test it on copies of the
     owner's real files first, and check that a second run STOPs.
   - Rehearse the owner's exact PowerShell steps on a fresh copy of the repository with
     the PowerShell tool before handing over.
   - Then: tests to `test_output.txt` with the expected last line; `python manage.py
     init-db` with the expected version and newly registered sources; the real-data
     commands with expected numbers; commit and push.
   - Commit messages end with `-m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`.
   - `git add src tests migrations config stages docs manage.py` (never `data/`).
7. When the owner says "done": verify directly - `git log`, `git status`, HEAD equals
   origin/main, the last line of `test_output.txt` (UTF-16), `diff -q --strip-trailing-cr`
   of every changed file against the tested copy, read-only DB queries
   (`sqlite3.connect("file:data/equity.sqlite?mode=ro", uri=True)`), `logs/app.log`, and CI.
8. Tooling pitfalls learned:
   - The Write tool turns a literal `\ufeff` into a real BOM, `\b` into a backspace and
     `\uXXXX` escapes into real characters - use `chr(0xFEFF)`, and run the escape script.
   - Bash heredocs mangle backslashes (`\\n`, `\\s`) - write scripts with the Write tool.
   - Python print of non-ASCII on this machine needs `PYTHONIOENCODING=utf-8`.
   - PowerShell 5.1: no `&&`; pass arguments to Start-Process as an array.
   - Static rules: `date.fromisoformat` only in `core/dates.py` (`strict_iso_date`);
     missing-data class names and extraction-confidence values are never string literals
     outside their home modules; the bare token REVIEW is banned in `src/`; network
     imports only in news_fetch.py; no `investment_confidence` identifier in a module
     that touches extraction confidence.
   - GDELT rate-limits hard: keep research requests few and minutes apart.
   - PDFs: there is no reportlab/poppler; render Markdown to HTML (`tools\md2html.py`) and
     print with headless Edge (`--headless=new --no-pdf-header-footer --print-to-pdf=...`).

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
| (handoff) | f0ed7ff | - | first handoff notes |
| 10 | 6c2a2f7 | 40B step 9, 4A, 4B.4, ADR-005 | news headlines from GDELT; extraction confidence stored apart from investment confidence; rules nw-entity-1 (company links) and nw-dedup-1 (copies) |
| 10B | ac0633f | 40B step 9, 4A, 5B, ADR-006 | SEBI releases from its RSS feed; public only from the first read; companies by exact registered name (sb-entity-1); kinds from SEBI's sections (sb-kinds-1) |
| arch v2.2.0 | see git log | 46, ADR-007 | architecture amended by insertion only; control audit test in CI; this handoff |

Acceptance records with exact claims, not-claimed items and negative assertions are in
`stages/STAGE_*_acceptance.yaml` (statuses such as ACCEPTED_NEWS_EXTERNAL_BASELINE for
Stage 10 and ACCEPTED_REGULATOR_RELEASES_BASELINE for 10B).

## 7. Current state (verified 2026-10-03)

- Tests: 393 at Stage 9; 482 after Stage 10; 518 after 10B; 521 after the v2.2.0
  install. Per file after the install: architecture_baseline 3, stage01 5, stage02 19,
  stage03 47, stage04a 12, stage04b 27, stage05 30, stage06 31, stage07a 25, stage07b 38,
  stage07c 45, stage07d 15, stage08 23, stage08b 19, stage08c 10, stage08d 19, stage09 25,
  stage10 89, stage10b 36, static_rules 3.
- Schema version 16; migrations 0001-0016 (create source registry, entities,
  source_class, data_trust, pit_facts, historical_universe, market_adapters,
  corporate_actions, corporate_action_files, identity_bridges, financial_results,
  integrated_filings, revision_corrections, announcements, news, sebi_releases), 32 files.
- Sources registered (11): nse_bhavcopy_equity, nse_corporate_actions,
  nse_index_constituents, nse_equity_list, nse_financial_results_index,
  nse_financial_results_xbrl, nse_integrated_filing_index, nse_integrated_filing_xbrl,
  nse_announcements, gdelt_doc_news, sebi_rss.
- Data: 2,594 entities (from EQUITY_L) with 2,593 NSE-symbol aliases; 34 raw files
  (integrated-filing XBRL 14, bhavcopies 6, integrated-filing listings 4, old results XBRL
  3, SEBI feed reads 2, announcement listings 2, old results listing 1, equity list 1,
  corporate actions 1); 13,806 trusted daily prices over 6 trading dates (20-Aug to
  01-Oct-2026 - far too short for any learning, see step 6a); 380 quarantine rows (kept as
  history); 1,182 corporate actions; 1 identity bridge (TAALTECH); results listings 5 (old
  page) + 49 (integrated); 17 results files loaded; 751 fundamental figures (2 stored as
  missing) - HDFC Life 300, Bajaj Finance 222, HDFC Bank 147, TCS 42, VST Tillers 21,
  Reliance 19; 5,903 announcement filings forming 5,723 events; 30 SEBI releases from 2
  reads (03-Oct-2026 12:15 and 15:06 India time - the second found all 30 already
  present, so no gap warning); GDELT news: 0 (first fetch not run yet); news names: 0
  recorded (fetch-news records them on first run from config/news_names.yaml).
- Historical-universe tables exist but hold no versions yet (universe_versions 0).
- `data/inbox` holds 32 files (all ingested); `data/fetched` holds the 2 SEBI reads;
  `data/raw` holds every raw file by sha256; `data/checklist.html` is the download page.

## 8. Code map

- `manage.py` - commands: init-db, sources, load-equity-list FILE, ingest-prices FILE...,
  load-corporate-actions FILE, compare-series SYMBOL START END, bridge-isins,
  load-results-index FILE..., load-results FILE..., show-fundamentals SYMBOL [PERIOD_END],
  load-announcements FILE..., show-events SYMBOL [FROM] [TO],
  fetch-news [--symbols A,B] [--from DATE], show-news SYMBOL [FROM] [TO],
  fetch-sebi, show-sebi [--symbol SYMBOL] [FROM] [TO],
  ingest-inbox [--without-listing] [FOLDER], checklist [LISTING...] [--symbols A,B]
  [--since DATE] [--prices-from DATE], report.
- `src/core/` - config, database (`connect`, `migrate`, `rollback`, `run_in_transaction`,
  `now_utc`), dates (`strict_iso_date`), logging_setup, status (2A vocabulary,
  `load_acceptance_records`; status must be a fixed status or ACCEPTED_<X>_BASELINE; every
  not_claimed and negative_assertions entry must be exactly false).
- `src/data_quality/` - missing_data (`MissingClass`: not_applicable, not_yet_released,
  not_disclosed, extraction_failure, source_conflict, structurally_absent), trust_chain
  (`NoDataError` ...), extraction_confidence (`ExtractionConfidence`, 4A rule 4:
  name_in_headline_and_link, name_in_a_list, name_in_headline_only, name_in_link_only,
  several_companies_named, no_name_found, registered_name_in_title).
- `src/provenance/` - availability (`disposition(claim, decision_time, retrieved_at,
  published_at)`, `PitClaim.CURRENT_DECISION/HISTORICAL_REPLAY`, `Availability`,
  `parse_timestamp` - timezone mandatory), raw_store (`store_raw_artifact`, sha256 dedup -
  identical bytes raise ArtifactError), pit_store (`record_fact`, `record_correction`,
  `fact_as_of`; UNITS include INR, INR_per_share, ratio).
- `src/universe/` - entities (`resolve(conn, identifier, as_of, alias_type=...)`;
  ALIAS_TYPES nse_symbol, bse_code, vendor_id, company_name, news_name), equity_list,
  historical_universe, identity_bridges.
- `src/ingestion/` - source_registry (REQUIRED_FIELDS, ALLOWED_VALUES, excluded source
  classes private_tip_channel / unattributed_rumour / non_public_information,
  `sync_sources` never silently changes a registration), market_adapters
  (`read_raw_table`, providers, `ingest_market_file`, `retry_quarantined`),
  corporate_actions + nse_corporate_actions (`normalise_name`: lower case, punctuation to
  spaces, 'limited' -> 'ltd'), nse_financial_results (OLD_INDAS and SEBI_FORMATS
  IndAS/Banking/NBFC/LI, listings, identities, standalone-only ratios, revisions, `IST`),
  intake (checklist + ingest-inbox), nse_announcements (filings, `events()`,
  EVENT_TYPES/REGISTERED_TYPES of 4A.0), gdelt_news (section 9), news_fetch (the only
  network code, sections 9 and 10.1), sebi_releases (section 9.7).
- `src/features/price_series.py` - raw/adjusted series.
- Empty packages reserved for later steps: abstention, calibration, experiments, ledger,
  models, regimes, research, targets, validation.
- `config/` - settings.yaml, sources.yaml (11 sources), news_names.yaml (section 9.2).
- `stages/` - one acceptance record per stage. `docs/decisions/` - ADR-001..007.

## 9. Stage 10 (news from GDELT) and Stage 10B (SEBI) in detail

### 9.1 Why GDELT
Commercial Indian news sites forbid AI use or automated reading (rule 9). GDELT's terms:
"unlimited and unrestricted use for any academic, commercial, or governmental use of any
kind without fee", with citation and a link to gdeltproject.org (recorded in the source
registry). The DOC 2.0 API (article list, JSON) gives per article: url, url_mobile,
title, seendate, socialimage, domain, language, sourcecountry. Only headline, link,
site, language, country and first-seen time are used.

### 9.2 News names (config/news_names.yaml, human-owned)
HDFCBANK INE040A01034 [HDFC Bank] from 1995-11-08; TCS INE467B01029 [Tata Consultancy
Services] from 2004-08-25; RELIANCE INE002A01018 [Reliance Industries, RIL] from
1995-11-29; BAJFINANCE INE296A01032 [Bajaj Finance] from 2003-04-01; HDFCLIFE
INE795G01014 [HDFC Life] from 2017-11-17; VSTTILLERS INE764D01017 [VST Tillers] from
2011-06-20. Not used on purpose: 'TCS' (also "tax collected at source"), 'HDFC' (several
companies), 'Reliance' (Reliance Power, Reliance Infrastructure and others are listed).
`sync_news_names` (run by fetch-news) records them as entity_aliases of type news_name;
refuses a name declared for two companies, a name equal to ANOTHER company's registered
name (e.g. 'Bajaj Housing Finance' for Bajaj Finance), a symbol that does not resolve to
the given ISIN, a bad shape (3-60 letters, digits, spaces, & . ' -), or any change to a
recorded name ("never silently changed"; closing a name is not supported yet).

### 9.3 Rule nw-entity-1 (which company an article is about)
`EntityReader` looks for declared names and each declared company's registered name
(from its first declared valid_from) in the headline words and in the link's path words
(letters and digits of any script; Indian vowel signs stay inside words). Where names
overlap the longest wins and a declared name wins a tie. A company is the SUBJECT only
when its name is in both headline and link, it is not next to a list comma in the
headline (commas between digits like '13 , 000' do not count), no other declared company
is named, and no other listed company is recognised in the headline - by a registered
name of two or more words (case-insensitive) or an NSE symbol of 3+ letters written in
capitals. Otherwise MENTIONED (name_in_a_list, name_in_headline_only, name_in_link_only,
several_companies_named); no declared name -> UNASSIGNED (no_name_found). Recognising
another company only ever withholds 'subject'. Five real headlines are regression tests:
'Stocks in news : Infosys , HDFC Bank , Jio Financial , IRFC , NCC and Blue Dart';
'HDFC Bank , Infosys , ITC shares : FPI favourites hit ...'; 'Suzlon , KPIT Tech , RIL ,
IRFC , HDFC Bank , Infy : 56 % Nifty500 stocks in bear grip ...'; 'HDFC Bank , Kotak
Mahindra Bank put two Anups atop banking big succession puzzle'; 'SBI Life , Max Fin ,
HDFC Life , LIC share price targets ...'. Known strictness: an aside ('Meet Anup Bagchi ,
HDFC Bank new MD & CEO') also counts as a list item; symbols such as BSE, OIL, ONGC, PSB,
INFY, TCS in capitals withhold 'subject'.
Extraction runs: `nw_extraction_runs` keyed by (rule, reader_version) where
reader_version hashes the declared names AND the registry (entities, symbols); a change
starts a new run over all articles, old runs stay; `stories()` raises NewsNotReadError
until `extract()` has run for the current version (commands call it).

### 9.4 Rule nw-dedup-1 (copies of one story) and availability
Copies = same headline word for word (casefolded letters/digits of any script),
distinctive (>= 6 words and >= 30 characters), each within 72 hours of the story's first
copy; computed from what was known at the decision time. Real cases: wire stories on two
sites, ET's story in two sections 11 hours apart, print and web editions, sharemanthan.in
republishing one HDFC Life article under ~10 addresses over 33 hours, and two different
Gujarati headlines that an early draft (Latin letters only) made look identical.
Availability: `available_at = min(seendate + 15 minutes, our retrieval)`; current
decisions use retrieval time; replay uses available_at.

### 9.5 Responses, storage and the fetcher
- A response is refused whole (nothing stored) if empty (`{}` or no articles ->
  NoDataError), GDELT's 'Please limit requests' text (RateLimitNotice), not UTF-8, not
  JSON, or not an article list. Articles are refused and recorded (nw_problems) for a
  missing field, a non-web link, a bad seendate, seen after retrieval, or seen outside the
  requested window (+-15 min). The same link again must agree, else 'article_conflict'.
  A response with 250 articles is recorded as complete=0.
- Tables (migration 0015): nw_responses (artifact, isin searched, query, window,
  counts, complete), nw_articles (url UNIQUE, title verbatim, domain, language,
  source_country, seen_at, available_at), nw_retrievals (which response returned which
  article), nw_problems, nw_extraction_runs, nw_extractions (role subject / mentioned /
  unassigned with CHECK constraints tying role and extraction_confidence). All
  append-only. No investment confidence anywhere (40B step 9 acceptance; static test).
- Story object (`stories(conn, decision_time, claim, isin)`): story_id, published_at,
  headline, language, copies, companies {isin: role, extraction_confidence, evidence},
  unassigned, searched_for, novelty {copies, sites, rule, repeats_an_exchange_filing:
  not_assessed}, source_quality {source, reliability_rating B, site_quality
  not_assessed}, event_type / direction / materiality / expected_horizon: not_assessed.
- news_fetch.py: ALLOWED_HOSTS {api.gdeltproject.org, www.sebi.gov.in}; API
  https://api.gdeltproject.org/api/v2/doc/doc; query per company = its names as quoted
  phrases joined with OR (no country filter); mode artlist, format json, maxrecords 250,
  sort datedesc, startdatetime/enddatetime YYYYMMDDHHMMSS; USER_AGENT
  'ai-equity-agent/1.0 (personal research, non-commercial)'; no redirects
  (`_NoRedirect`); MIN_INTERVAL 20 s; REFUSAL_WAITS 60, 180, 300 s, then RateLimited and
  the Fetcher asks nothing more that run (gave_up); a 250-article response is split in two
  until the window is under 2 hours; SEARCH_WINDOW 90 days; first fetch per company 7
  days, later from the last stored window end minus 1 day; responses saved as
  data/fetched/gdelt_<SYMBOL>_<start>_<end>.json and kept as raw artifacts.

### 9.6 Stage 10 real-data numbers and verifying the owner's first fetch
3 real responses fetched 02-Oct-2026 (HDFC Bank 1 week, Reliance Industries 1 week,
HDFC Life 4 weeks; Indian outlets): 340 articles returned, 304 stored (36 returned by
two searches), 0 refused, 61 sites, English 216 / Hindi 77 / Marathi 6 / Gujarati 5;
273 stories; 15 articles (14 stories) about one company - 13 HDFC Bank (mostly Anup
Bagchi's appointment as MD and CEO) and 1 Reliance bond issue, every one checked by
reading; 38 articles only mention a company; 251 unassigned. On 03-Oct-2026 a real
fetch-news run on a database copy (VST Tillers) was refused 5 times over 16 minutes and
reported NOT FETCHED - nothing stored. When the owner says "fetched": read logs/app.log
for the run, count nw_responses / nw_articles / nw_extractions by role, list
`show-news HDFCBANK` subjects and check them by reading, and confirm no problems rows.

### 9.7 Stage 10B (SEBI) design
- Feed https://www.sebi.gov.in/sebirss.xml: RSS 2.0, ttl 60, latest 30 items (about three
  working days); title, description (= title), link, pubDate as a date only
  ('01 Oct, 2026 +0530'); links like /enforcement/orders/oct-2026/<slug>_<id>.html.
  SEBI website policy: linking needs no permission, reproduction needs permission by
  email - we store privately and never republish. robots.txt allows all.
- sebi_releases.py: refuses a feed with DOCTYPE/ENTITY, non-RSS, no channel, or no items
  (NoDataError); items refused for no title, a link outside SEBI's site, an unreadable
  date, or a date after the read (India date). Release stored once by link; read again
  differently -> 'item_conflict'. A read sharing no release with the previous read sets
  overlaps_previous=0 and warns "may have been missed". Availability = this system's
  first read of the release (SEBI gives no time) under both claims; SEBI's date kept as
  stated_date.
- Rule sb-kinds-1 (SECTION_KINDS): enforcement/orders -> order, event type sebi_order;
  enforcement/recovery-proceedings -> recovery_proceeding; legal/circulars -> circular;
  media-and-notifications/press-releases -> press_release; anything else -> other.
- Rule sb-entity-1 (`NameReader`): a listed company is 'named' only when its registered
  name appears word for word (normalise_name: 'Ltd' = 'Limited', case and punctuation
  ignored; an apostrophe splits a word, so 'Dr Reddys' does not match "Dr. Reddy's");
  names without a company suffix (PSU banks, LIC, GIC) must appear exactly as registered;
  longest name wins; a name shared by two registered companies (Taal Tech old/new ISIN,
  Future Enterprises, GACM, Jain Irrigation) links neither. Extraction confidence
  registered_name_in_title; role 'named' (target vs subject not assessed).
- Tables (migration 0016): sb_reads, sb_releases (link UNIQUE, title, stated_date,
  section, read_id), sb_problems - append-only.
- `fetch_sebi`: only SEBI_FEED (any other sebi.gov.in address is refused), refuses to send
  within 60 minutes of the last stored read (SEBI_WAIT), HTTP != 200 -> FetchError,
  checks the feed before writing data/fetched/sebi_<UTC time>.xml.
- Real data 03-Oct-2026: 30 items (01-Oct 15, 30-Sep 9, 29-Sep 6), 30 stored, 0 refused;
  16 orders, 12 recovery proceedings, 1 circular, 1 press release; companies named: SMC
  Global Securities (adjudication order) and TV Vision (two recovery notices);
  'Adani Group Companies' and 'Lloyd Enterprises Limited' (not the listed 'Lloyds
  Enterprises Limited') link nothing.

## 10. Architecture v2.2.0 (ADR-007) - what changed and why

The owner asked whether the model considers everything that moves Indian stocks and
whether it can give buy/hold/sell with expected percentage gains and keep improving. A
full re-read of v2.1.1 found: Sector/macro was Core (3B) but no 40B step built it; the
event types (4A.0) were company-level only; world markets were not named; no rule for
markets closing at different hours; return magnitudes were required in the ledger (21)
but never scored, and no rule mapped forecasts to BUY/HOLD/SELL; 40C described the
predecessor codebase. Changes (all insertions):

| ACR | Change | Section |
|---|---|---|
| 103 | Global and India macro context: rates and bonds (US 2Y/10Y, Fed, India 10Y G-sec, RBI repo and liquidity, Japan/euro rates), currencies (USD/INR, dollar index, CNY, JPY), commodities (Brent/WTI, gas, gold, copper, aluminium, steel inputs, agri), world equity markets (S&P 500, Nasdaq, Nikkei, Shanghai, Hang Seng, EM, GIFT Nifty), volatility and credit stress (VIX, India VIX, US high-yield spreads), economic releases (India CPI/WPI/IIP/GDP/GST/PMI, US CPI/payrolls/GDP, China), investor flows (FPI/FII, DII), monsoon, Budget, elections, MSCI/FTSE reviews. Context, never covered securities or benchmarks; two routes only (regime state, or measured company sensitivity) | 3B rule 4, new 3G |
| 104 | Cross-market timing: every series carries exchange, session calendar, time zone, publication time; available_at in UTC, never the calendar date; a closed foreign market is `structurally_absent`, never carried forward | new 5C |
| 105 | New event groups: monetary policy and rates; fiscal, trade and regulation; sovereign and macro data; geopolitics and shocks; index-provider and flow events. Rule 5: an event without an issuer reaches a security only by declared read-across, sector membership or measured sensitivity, recorded | 4A.0, 4A rule 5 |
| 106 | Macro exposure feature = measured company sensitivity x observed factor move, admitted as a Fundamental-family feature; raw macro levels stay routing-only | 9A, 9C |
| 107 | Regime engine: global risk appetite, US dollar and rates direction, commodity shock, foreign-flow state, geopolitical stress | 29 |
| 108 | New 40B steps before step 11: 6a price-history acquisition, 9a macro context, 9b macro and geopolitical events, 9c aggregate investor flows; built to a current-decision baseline first; 3F records the accepted delay of the effective-N clock | 40B, 3F |
| 109 | Data acquisition and network policy: terms first, free/official first, paid only on owner approval, no scraping, one network module with allow-list and no redirects, secrets never in chat/repo/logs/URLs/errors, every response kept, versioned acquisition contracts, excluded and display-only sources stay out | new 4G |
| 110 | Return forecasts: per registered horizon P(gain), P(outperform), absolute and excess return ranges (10/25/50/75/90th percentiles after costs), decision BUY/HOLD/SELL/ABSTAIN, invalidation condition; scored by pinball loss and CRPS, calibrated by interval coverage (10-90 range must hold the outcome ~80% of the time); a failing range is withheld; the decision rule is a preregistered human-owned artifact with owner-set thresholds; factor exposure labelled; improvement measured on live-origin calibration only | new 7A, 16, 18, 21 (return_quantiles, decision_rule_version, cost_model_version), 36, 37 (items 21-24) |
| 111 | Purpose and use: research for the owner's own decisions, never distributed as advice | 3 |
| 112 | 40C / "Current implementation position (v2.1.1)" describe the predecessor codebase; a new closing note gives this repository's position | 40C, end |
| 113 | Acceptance criteria 90-104 and guardrails 17-20 | 47, 47A |

Control audit: 4,152 -> 4,453 lines; 303 inserted, 0 deleted; replaced only the version
line and '5. This document is **frozen at v2.2.0** (previously v2.1.1).'; all 210
headings, every ACR id and criteria 1-89 kept. `tests/test_architecture_baseline.py`
re-runs the audit, checks criteria are exactly 1..104, and checks README.md and this file
name the v2.2.0 document. The build/audit/PDF scripts are in `data\handover\tools`
(build_v220.py, audit_v220.py, md2html.py).

What the owner was told and must keep being told honestly: the design produces
BUY/HOLD/SELL/ABSTAIN with calibrated probabilities and return ranges per horizon and
improves only when live calibration improves; nothing predicts anything until years of
price history exist (we have 6 weeks); profit is not guaranteed and "found no edge,
abstained" counts as success (49A); the assistant is not a licensed adviser.

## 11. Data-source research already done (do not repeat)

### 11.1 Exchange, brokers, vendors (2026-10-02)
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
- Global: Twelve Data Pro (~$229/month, verified on its exchange list: NSE/BSE, US,
  Tokyo, Shanghai/Shenzhen, forex, fundamentals; personal use); FMP Ultimate (~$99/month
  annual; India/Japan/China coverage not confirmed); EODHD does NOT list Indian or Tokyo
  exchanges and says its prices are indicative. Official free sources: SEC EDGAR (US),
  J-Quants (Japan, by JPX), filings.xbrl.org (Europe annual), ECB and FRED (FX/macro).
- Recommendation given: hand downloads + checklist for the 30-company cohort; NSE research
  request for history; authorised vendor quote for scale later.

### 11.2 News and regulators (2026-10-02/03)
- Business Standard terms: no automated collection, no caching/archiving, no use in any
  AI/ML system including grounding and RAG. HT Digital (Hindustan Times, Mint): no AI/ML
  use without a written licence, RSS feeds included. Economic Times: the browser and
  WebFetch are blocked from it. Moneycontrol: terms not read; treated as not allowed.
- GDELT: open data, any use with citation; DOC API last 3 months, 250 articles per call,
  'Please limit requests to one every 5 seconds' (enforced much more strictly in
  practice); GDELT bulk files and Google BigQuery hold older history (BigQuery free tier
  1 TB/month, needs a Google Cloud account).
- Paid news APIs (terms on storage and AI use NOT yet checked): Marketaux free 100
  requests/day x 3 articles, $29/49/99/199 per month; NewsData.io free 200 credits/day
  (12-hour delay, production use advertised), $199.99/349.99/1,299.99 per month;
  NewsAPI.org free plan for development only, $449/month business.
- PIB: material may be reproduced free of charge without prior approval, with prominent
  acknowledgement, not in a misleading context; third-party material excluded.
- SEBI: website policy as in 9.7; RSS page https://www.sebi.gov.in/rss.html.
- RBI: website terms - "caching and links to, and the framing of this Web Site or any of
  the contents are prohibited"; home page may be linked on written notice; internal pages
  need RBI's written permission. RBI's server answers HTTP 418 to AI tools by user agent
  but 200 to an honest program user agent. Feeds exist (pressreleases_rss.xml - 10 items
  with times but no timezone; notifications_rss.xml) - NOT used (ADR-006). The owner chose
  to skip RBI; a permission letter could be drafted later.

### 11.3 Alpha Vantage (2026-10-03)
- Terms (PDF at alphavantage.co/terms_of_service, opened in the browser it downloads):
  free key for individual, non-commercial use; "commercial" = using it for a firm,
  providing information to others, or financial-industry affiliation - none applies. No
  clause on storage or AI use found in the readable text (extraction was partial). AV
  markets its news for training LLMs.
- Free key 25 requests/day; premium $49.99/99.99/149.99/199.99/249.99 per month (75 to
  1,200 requests/min), annual about 2 months off.
- NEWS_SENTIMENT: tickers, topics, time_from/time_to (YYYYMMDDTHHMM), sort, limit up to
  1000; fields title, url, time_published, authors, summary, banner_image, source,
  category_within_source, source_domain, topics with relevance, overall_sentiment_score
  and label, ticker_sentiment (ticker, relevance_score, ticker_sentiment_score, label);
  labels: <= -0.35 Bearish, -0.35..-0.15 Somewhat-Bearish, -0.15..0.15 Neutral,
  0.15..0.35 Somewhat_Bullish, >= 0.35 Bullish. The AAPL demo returned mostly US/Canada
  sites (MarketBeat, Investing.com Canada, Benzinga, Yahoo Finance, TradingView ...) and
  a first article about Honeywell - tagging is loose. Several tickers in one call mean
  "mentions all of them", so one call per company.
- Also: FX (CURRENCY_EXCHANGE_RATE, FX_DAILY), commodities (WTI, Brent, natural gas,
  gold/silver spot, copper, wheat ...), US economic indicators (REAL_GDP, TREASURY_YIELD,
  FEDERAL_FUNDS_RATE, CPI ... - sourced from FRED, FRED terms apply), index data (S&P 500,
  Nasdaq, Dow, VIX, Russell, others) and options on PREMIUM only, earnings-call
  transcripts, US insider transactions.
- Probe NOT run yet. Script: `data\handover\tools\av_probe.py` (5 requests 20 s apart:
  HDB, INFY, RELIANCE.BSE, TCS.BSE, topics=financial_markets; reads the key from
  ALPHAVANTAGE_API_KEY, never prints or saves it; saves answers to
  `data\handover\tools\av_samples\`). Owner commands:
  `$env:ALPHAVANTAGE_API_KEY = Read-Host "Alpha Vantage key"` then
  `python data\handover\tools\av_probe.py`, then reply "probed".

### 11.4 Macro sources (2026-10-03, for Stages 10C-10E)
- FRED API: free key; ALFRED keeps every vintage (realtime_start / realtime_end) - the
  answer to 5A.1 and 3G rule 1; series copyrighted by third parties (e.g. S&P 500, Nikkei
  225) may be used for personal non-commercial use without permission. Candidate series:
  DGS2, DGS10, DFF, T10Y2Y, DCOILBRENTEU, DCOILWTICO, DEXINUS, DEXCHUS, DEXJPUS,
  DTWEXBGS, VIXCLS, BAMLH0A0HYM2, SP500, NASDAQCOM, NIKKEI225, plus India monthly series
  (CPI, policy rate, 10Y yield) - to be confirmed on FRED in the Stage 10C research step.
- MoSPI eSankhyiki API (CPI, WPI, IIP, GDP and more): no key, government data; terms to
  record (Government Open Data License expected - check).
- FBIL (USD/INR reference rate, G-sec and T-bill benchmarks, MIBOR): terms to check.
- FPI/FII flows: NSDL publishes daily FPI investment data (since June 2014), also CDSL
  and SEBI's FPI statistics pages; NSE publishes provisional FII/DII cash-market figures
  (hand download only - NSE terms). NSDL terms to check.
- Not yet researched: GIFT Nifty data (NSE IX), India VIX history (NSE, by hand), MSCI
  announcements, IMD monsoon data, China data sources, sovereign rating feeds (licensed;
  use news).

## 12. Roadmap (40B order) and the next step in detail

Done: steps 1-9 (Stage 7 = step 6; Stage 8/8B/8D = step 7; Stage 9 = step 8; Stages
10/10B = step 9; 8C = intake tooling). Stage names for v2.2.0 steps: Stage 10C = step 9a,
10D = 9b, 10E = 9c, Stage 11 = step 10 (sentiment), Stage 7E = step 6a (price history,
alongside). Then step 11 Knowledge/Event Hub, 12 Real Feature Factory, 13 Real Target
Engine, 14 Equity Research Agent v0.1 (first agent), 15 Prediction Ledger, 16 Shadow
operation, 17 Outcome Resolver, 18 Error Attribution, 19 Calibration + Abstention,
20 Decay/Drift, 21 Controlled Self-Learning, 22 Specialist agents, 23 API + Orchestrator.

NEXT: Stage 10C = 40B step 9a, Global and India Macro Context Adapter.
- Acceptance (40B): "Every series carries session, time zone, publication time and
  vintages; a foreign close is not available to an Indian decision before it exists (5C)".
- Read first: 3B (rule 4), 3G, 4G, 5, 5A, 5B, 5C, 9A, 9C, 29, 25A and the 'Changes in
  v2.2.0' table.
- Research step (method section 5): confirm each candidate series on FRED (frequency,
  units, time of observation, release lag, vintage availability in ALFRED, copyright
  notes); MoSPI API terms and formats; FBIL terms; India VIX and Nifty index files from
  NSE (hand download). Ask the owner for permission before fetching samples, and ask them
  to create the FRED key (never pasted in chat).
- Design notes to carry in: a series registry (series id, source, exchange or
  publisher, session calendar, time zone, unit, frequency, vintage policy); observations
  stored with value time (local and UTC), available_at, retrieval time, vintage
  (realtime_start/end) and raw artifact; missing values classified (closed market ->
  structurally_absent); the fetcher gains FRED/MoSPI hosts only via a new ADR (ADR-008)
  and allow-list tests; the key is read from the environment (or an untracked file) only
  inside news_fetch.py (or a renamed binding, keeping the single-network-module rule and
  its tests - 40F: prefer binding to rename); FRED key never in stored URLs or errors.
- After 10C: 10D (macro and geopolitical events - GDELT themes/timelines for conflict,
  oil, sanctions; PIB; SEBI), 10E (FPI/FII and DII daily flows), then Stage 11 sentiment
  (Alpha Vantage after the probe; exclude TradingView; 4B: liquidity threshold from
  trusted_prices, sentiment only over sentiment-eligible 'subject' stories, raw model
  output kept and never flipped).

## 13. NSE real-data findings (the code depends on these)

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
Registry names (for news and SEBI matching): legal names include ordinary words ('Take
Solutions', 'Eternal', 'Nile'); 16 have no Limited/Ltd (PSU banks, LIC, GIC,
'Century Extrusions Limited-RE', 'Federal-Mogul Goetze (India) Limited.'); NSE symbols
that are ordinary capitalised words include BSE, OIL, ONGC, PSB, INFY, TCS, IDEA.

## 14. Open items, deferred work and things NOT claimed

- Rows refused by an earlier code version cannot be re-read from a stored listing
  (a later fix needs a re-download with new bytes). Consider a reprocess tool.
- Per-share figures are not adjusted for bonuses/splits; balance sheet and cash flow
  not stored; segment results not stored; half-year/nine-month periods not stored.
- NBFC GS3/AUM and insurer VNB/APE are not in the XBRL files.
- Announcements: duplicates judged by file name and timing, not PDF bytes; direction,
  materiality and horizon not assessed; unclassified subjects not read from text;
  no BSE cross-exchange syndication. 125 announcement rows (52 symbols) were refused:
  companies not in EQUITY_L.
- News (Stage 10): headlines only, article text never read; event type, direction,
  materiality and horizon not assessed; news repeating an exchange filing not recognised;
  short forms ('Reliance', 'TCS', 'HDFC') and names only in other scripts not matched;
  'sources say' stories not screened (4F.2); instruction-shaped text not detected or
  recorded against a source (4D rule 4); site quality not assessed; extraction runs not
  filtered by decision time; only 6 companies have news names; closing a news name not
  supported; no older history than GDELT's 3 months.
- SEBI (Stage 10B): titles only; releases before the first read are missing; whether a
  named company is the party acted against is not assessed; circulars not linked to
  sectors; no RBI.
- Whole system: no sector classification yet (needed by 3G rule 4 and 9B); no 30-company
  cohort chosen; price history only 6 trading days; universe versions empty; steps 11-23
  not started; nothing is predicted yet.

## 15. Files kept for the next chat (`data\handover\`, git-ignored, on disk)

- `HANDOFF_new.md` - this file (installed as docs/HANDOFF.md by the installer).
- `install_v220.py` - checked installer for v2.2.0 + this handoff (section 0.1).
- `arch220_files\` - docs/Master_Architecture_v2_2_0_FROZEN.md and .pdf,
  docs/decisions/ADR-007-architecture-v2-2-0.md, tests/test_architecture_baseline.py
  (the reference copies to diff against after the install).
- `tools\` - build_v220.py, audit_v220.py, md2html.py (architecture build, audit, PDF);
  mutate_stage10.py, mutate_stage10b.py (deliberate-fault scripts; edit ROOT to point at a
  scratch copy); smoke_news.py, smoke_sebi.py, analyse_gdelt.py, analyse_sebi.py (real-data
  checks on database copies); escape_tests.py (non-ASCII -> \u escapes); pdf_text.py;
  fetch_gdelt_samples.py (research fetcher, for reference only - do not hammer GDELT);
  av_probe.py (section 11.3).
- `research\` - the real samples: gdelt_samples\ (HDFC Bank, Reliance, HDFC Life JSON and
  the fetch log) and sebi_samples\ (feed read of 03-Oct-2026 with headers), and
  av_terms.txt (partial text of Alpha Vantage's terms).

## 16. How to start the new chat

Paste this to the new chat:

> I am continuing my AI equity research agent project at
> C:\Users\nalin\Projects\ai-equity-agent. Please read docs/HANDOFF.md fully first (if
> data\handover\HANDOFF_new.md is newer or the v2.2.0 architecture is missing from docs,
> read that one and finish its section 0.1 first), then the frozen architecture
> docs/Master_Architecture_v2_2_0_FROZEN.md sections named there. Verify the current state
> (git log, tests, database version 16, CI), then continue with Stage 10C (architecture
> 40B step 9a, Global and India Macro Context) using the same step-by-step method:
> research real data first, build and test in a scratch copy, give me paste blocks and
> commands, and verify after I reply "done". Tell me in advance whenever you need an API
> key and from which source - free options first.
