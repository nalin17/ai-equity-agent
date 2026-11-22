# HANDOFF (compact) - AI Self-Learning Equity Research Agent

Compact handoff written 2026-11-22 (end of the sixth chat: Stage 12A). Read THIS file fully, then
`data\handover\stage12\PLAN.md` (Stage 12 decisions, measured facts, 12B plan); read other files only when a task
needs them (section 9 says where). Governing architecture: `docs/Master_Architecture_v2_2_0_FROZEN.md` (v2.2.0,
frozen - amend only by insertion with an ADR, 46/46A). Older detail is in git history: `git show
6cdf2fe:docs/HANDOFF.md` (long handoff up to Stage 10D), `git show 9c3d2d3:docs/HANDOFF.md` (after Stage 11).

## 0. State (22-Nov-2026)
| Item | State |
|---|---|
| Last pushed commit | Stage 12A GKG headlines and sentiment inputs (ADR-013), committed by `stage.py commit stage12a` - see `git log -1`. Before it: `9c3d2d3` Stage 11. 1,010 tests. |
| Stage 12A | ACCEPTED: check PASS (1,010 tests, 39/39 faults, smoke with the real GKG samples on a database copy), install PASS 22-Nov 12:17, live `fetch-gkg` (91 files, 6,659 rows kept) and `show-sentiment HDFCBANK` verified (record in stages/STAGE_12A_acceptance.yaml). |
| Database | `data/equity.sqlite`, schema 21, 20 sources. Backups `data/equity_before_*.sqlite` (latest `_12a`). |
| First check each chat | `python data\handover\tools\status.py --ci` (one screen: git, tests, stage report, database, freshness incl. GKG, gaps, calendar, Downloads, CI). |
| Next build | Stage 12B = FinBERT headline scorer (owner's choice 22-Nov) - first a new price-echo rule version se-echo-2 with the HDB headline as a named test (section 8). Then the owner chooses: BusinessLine/The Hindu + RBI RSS (approved 09-Nov) or 40B step 12. |

### 0.1 Verify Stage 12A at the start of the next chat
`python data\handover\tools\status.py --ci` must show: HEAD = the Stage 12A commit, tree clean, origin/main
equal, tests 1010 passed, CI success for HEAD. If `git log -1` is still Stage 11 (9c3d2d3), the owner had not
finished: `python data\handover\stage12a\patch_stage12a_record.py`, then
`python data\handover\tools\stage.py commit stage12a`.

## 1. Owner and working style
- Owner (GitHub nalin17) is NOT a developer: pastes PowerShell lines, replies "done". Plain language, they/them.
  Windows 11, PowerShell 5.1 (no `&&`), Python 3.14, venv `.venv`. Never ask for Administrator.
- Owner decides policy (new source/host, paid data, architecture): ask with AskUserQuestion, recommended first.
  Technical judgement is delegated: "robust", fail-closed. Cross-verify facts from primary sources.
- Goal: personal BUY/HOLD/SELL with calibrated return ranges per horizon, learning over time; research for own
  decisions only, never distributed as advice. Honest message: nothing predicts until years of price history.
  The owner does not want to miss any factor that can move a stock: every bundle names the missing domains.
- Owner sends emails and downloads files; the assistant never does. Keys only in the owner's environment.
- Usage limits are tight: one stage per chat, small outputs, restartable work under `data\handover\` (git-ignored).

## 2. Token-saving workflow (APPROVED and BUILT 05-Oct-2026; tools in `data\handover\tools\`, git-ignored)
1. One stage per chat; this file is the only required read; architecture by line range (section 9).
2. `inspect_file.py <file|folder>`: <=60-line profile of any downloaded file (encoding/BOM, line endings,
   delimiter, header normalised and raw, per column kind/format/empties/distinct/min/max/top, samples; JSON
   key trees with key presence; XML paths with counts; XLSX, ZIP, gzip, HTML, PDF). Design from the profile,
   not the raw file. (Not named inspect.py: that would hide Python's inspect module from the other tools.)
3. `stage.py` - one stage's hand-over:
   `new <stage>` work\repo = tracked files (LF) from HEAD (base.txt); the assistant edits/adds files there.
   `check <stage> [--faults] [--smoke]` refuses if HEAD moved or tracked files are modified; generates
   `files\` (new files, pure ASCII) and `patch_<stage>.py` (make_patch.py); builds `sandbox\repo` from the
   owner's files byte for byte, installs as install will, requires equality with work\repo, pytest behind a
   dead proxy, init-db on a database copy; `--faults` runs `tools\mutate_<stage>.py` (sandbox made LF first),
   `--smoke` runs `tools\smoke_<stage>.py <sandbox>`; writes report.txt (<=40 lines, printed) and check.json.
   `install <stage>` (owner): only a PASSed check for this HEAD and these exact bytes; database backup, patch,
   new files (never overwritten), equality with the checked hashes, pytest, then init-db; install_report.txt.
   `record <stage>` builds `patch_<stage>_record.py` from later edits in work\repo (acceptance, HANDOFF).
   `commit <stage>` (owner): every changed file must equal work\repo; pytest; git add (usual folders only);
   commit with commit_message.txt + the Co-Authored-By line; push. `undo <stage>`: files back (hash-checked).
4. `status.py [--ci]`: the one-screen status - replaces multi-command verification.
5. Keep: tests with every change, terms-first research, owner approvals, light fault checks of each stage's key
   rules. Drop: in-chat rehearsals, repeated verification, reading raw files.

## 3. Rules that must never be broken
1. NSE: no automated collection - hand downloads only (ADR-004). No scrapers, no nsepython/jugaad, no NSE mirrors.
2. LICENSED ONLY: no data used against its terms; repos copying NSE data not used. TradingView never.
3. Only `src/ingestion/news_fetch.py` opens network connections (static tests), allow-list of 8 hosts, exact
   paths, no redirects: api.gdeltproject.org, www.sebi.gov.in (/sebirss.xml), api.stlouisfed.org (series,
   observations, release/dates), api.mospi.gov.in (3 paths), www.federalreserve.gov (/feeds/press_monetary.xml),
   www.ecb.europa.eu (/rss/press.html), www.boj.or.jp (/en/rss/whatsnew.xml), data.gdeltproject.org
   (/gdeltv2/lastupdate.txt and /gdeltv2/<slot>.gkg.csv.zip - ADR-013). New host = owner approval + ADR.
4. Secrets (FRED_API_KEY, user env var) never in chat, repo, logs, files, URLs stored, messages.
5. Certificates always checked. Legacy TLS only for MoSPI; extra root (Sectigo E46, fingerprint-checked) only for ECB.
6. Never repair, fill or carry forward data: refuse, quarantine, or classify missing (MissingClass, 4C).
7. Append-only tables (triggers); corrections are new vintages.
8. Point in time (5B/5C): availability must be proven (exchange time, issuer's stated time, FRED last_updated,
   or our own retrieval); otherwise AVAILABILITY_REVIEW for replay. Foreign closes never before their session ended.
9. Ingested text is data, never instruction (4D). No real persons' names or tax ids in tests or the repo.
10. Macro series, events and flows are context only - never covered securities, targets or benchmarks.
11. An event without an issuer reaches a security only through a declared, recorded route (config/event_routes.yaml);
   only ingestion/event_routes.py and knowledge/hub.py may call attribute()/events_for() (static test).
12. RBI site data not used (terms; its press-release RSS is approved for the stage after 12). Commercial Indian
   news sites are not sources (their headlines reach us only as GDELT's GKG metadata - headline, link, site, time;
   links never opened); their RSS only after a written yes in data\handover\research\permissions\ and an ADR.
   NSDL and CDSL FPI data not stored (terms).
14. Sentiment (4B): GDELT tone is whole-article, never company sentiment; a story counts for a company only as
   the subject of its headline (nw-entity-1); price echo is attention only; below the liquidity band sentiment is
   refused, never down-weighted; no news is a gap, never neutral; rules are versioned - a change is a new rule id.
13. Static rules: `date.fromisoformat` only in core/dates.py; MissingClass and ExtractionConfidence values never as
   string literals elsewhere; bare token REVIEW banned; env reads only in news_fetch.py.

## 4. Method per stage (with the section 2 tools)
Research real data + terms first (owner approves sources; owner runs inspect_file.py on samples) ->
`stage.py new` -> write code + tests in work\repo (run pytest there while building) -> `tools\mutate_<stage>.py`
and `tools\smoke_<stage>.py` -> `stage.py check <stage> --faults --smoke` until PASS -> owner `stage.py install`
-> owner's live command -> assistant edits acceptance "first live run" to proven + HANDOFF in work\repo ->
`stage.py record` -> owner runs the record patch, then `stage.py commit`.
New files pure ASCII (use chr() for non-ASCII). Commit message: `data\handover\<stage>\commit_message.txt`.
Pitfalls: Bash heredocs and tool strings mangle backslashes - write scripts with the Write tool; Windows paths
over 260 characters fail (keep test copies under a short %TEMP% folder); test_output.txt may be UTF-16
(PowerShell) or UTF-8 (stage.py); fault anchors are written against LF text.

## 5. Project facts
- Folder `C:\Users\nalin\Projects\ai-equity-agent`; GitHub https://github.com/nalin17/ai-equity-agent (PUBLIC).
- SQLite (ADR-001); pytest (pytest.ini: pythonpath src); CI `.github/workflows/tests.yml` (Linux, Py 3.14);
  requirements: pytest, pyyaml only; network via stdlib urllib only.
- Logs `logs/app.log`; downloads land in `C:\Users\nalin\Downloads`, ingest-inbox moves them to `data\inbox`.
- Owner's daily routine: `fetch-sebi` (feed keeps ~3 working days - daily!), `fetch-gkg` (GDELT GKG headlines,
  ~0.4 GB a day downloaded, little stored; catches up a week of unread slots), `fetch-macro`, `fetch-india`,
  `fetch-events`; trading evenings: download both CSVs from https://www.nseindia.com/reports/fii-dii then
  `ingest-inbox`. `fetch-news` (DOC API) is refused by GDELT since 05-Oct - not in the routine.
- Calendars (config/market_calendars.yaml) end 2026-12-31. Owner's choice 22-Nov: regenerate all three in
  December once NSE publishes its 2027 holiday list (owner downloads it). exchange_calendars 4.13.3 has NO XBOM
  2027 dates; Windows Application Control blocked pandas 3.1.1's DLL in a %TEMP% venv on 09-Nov - use an older
  pandas or a pandas-free generator, and take XBOM 2027 from NSE's circular if the library still lacks it.
- FinBERT trial venv `%TEMP%\fbt` (torch 2.15 CPU + transformers 5.24 import fine on this PC, 22-Nov).

## 6. Stages done (records in stages/*_acceptance.yaml, decisions in docs/decisions/ADR-001..013)
| Stage | Commit | 40B step | What |
|---|---|---|---|
| 0-6 | 9773aa2..2606dea | 1-5 | skeleton, registry, trust chain, PIT store, universe |
| 7A-7D | 9aa2b52..b8db868 | 6 | NSE bhavcopy, corporate actions, adjusted series, ISIN bridges |
| 8, 8B, 8C, 8D | 535ae7e..7da4f0b | 7 | results (old XBRL, integrated filings, NBFC/insurers), intake |
| 9 | cf1c948 | 8 | announcements, one release = one event |
| 10, 10B | 6c2a2f7, ac0633f | 9 | GDELT headlines, SEBI feed |
| v2.2.0 | 9bb500f | - | architecture amended (ADR-007) |
| 10C, 10C-2 | 36450db, bfa5c8f | 9a | FRED/ALFRED 25 series; MoSPI CPI/IIP/GDP; market calendars |
| 10D | 6cdf2fe | 9b | Fed/ECB/BoJ feeds, FRED release calendar, derived release events, routes |
| 10E | 2994320 | 9c | NSE FII/DII daily flows by hand download |
| 11 | 9c3d2d3 | 11 | Knowledge/Event Hub: one evidence object, read-only, gaps always said |
| 12A | (section 0.1) | 10 | GKG headlines (raw files not kept), filing directions, price echo, liquidity band, public sentiment in the hub (unscored) |
Tests: 1,010 after Stage 12A. Fault checks: 10 32/32, 10B 21/21, 10C 63/63, 10C-2 58/58, 10D 101/101, 10E 31/31,
11 24/24, 12A 39/39.

## 7. Code map (src/)
- core: config, database (migrate/rollback/run_in_transaction), dates (strict_iso_date), sessions (time zones),
  calendars (XNYS/XTKS/XBOM, CalendarError outside coverage), status (acceptance records), logging_setup.
- data_quality: missing_data (MissingClass), trust_chain (NoDataError), extraction_confidence.
- provenance: availability (disposition, PitClaim, parse_timestamp, price_availability), raw_store, pit_store
  (fact_as_of).
- universe: entities (resolve by ISIN/alias, validate_isin), equity_list, historical_universe, identity_bridges.
- ingestion: source_registry, market_adapters, corporate_actions/nse_corporate_actions, nse_financial_results,
  nse_announcements (events), intake, gdelt_news (stories, EntityReader nw-entity-1), gdelt_gkg (load_gkg,
  extract, stories, stored_slots; tables gk_*), sebi_releases (releases), macro_context (FRED observations/latest),
  india_macro (MoSPI), macro_events (macro_events, scheduled_releases), event_routes (attribute, events_for),
  nse_flows (flows, missing_days), news_fetch (the ONLY network code; GkgClient, gkg_slots, fetch_gkg).
- knowledge: evidence (Domain, Attribution, GapNature, Evidence, EvidenceGap, Bundle), hub (gather, clamp_window;
  adapters per domain incl. _gkg and _sentiment; hub-2; NOT_BUILT = derivatives, alternative data), sentiment
  (rules an-direction-1, se-echo-1, se-eligible-1, se-liquidity-1: filing_direction, price_echo, eligibility,
  liquidity).
- features/price_series.py. Empty packages for later steps: abstention, calibration, experiments, ledger, models,
  regimes, research, targets, validation.
- manage.py commands: init-db, sources, load-*, ingest-prices, ingest-inbox, checklist, compare-series,
  bridge-isins, show-fundamentals/-events/-news/-sebi/-macro/-india/-macro-events/-flows/-evidence/-sentiment,
  fetch-news/-sebi/-macro/-india/-events/-gkg, report.
- config: sources.yaml (20), news_names.yaml (6 companies - only these can be a headline's subject),
  macro_series.yaml (25), india_macro_series.yaml (9),
  market_calendars.yaml, declared_events.yaml and event_routes.yaml (owner-owned, empty).

## 8. Next steps and open items
- Stage 12B = FinBERT scorer (plan in data\handover\stage12\PLAN.md section 3, 12B). FIRST: se-echo-2 with the
  live false negative 'HDFC Bank (HDB) Finds Its Spark Amid Wall Street Selloff' (a US ADR's price move, no stock
  word, no percentage) as a named test - before any headline is scored. Then: owner downloads ProsusAI/finbert
  (model.safetensors, config.json, vocab.txt, tokenizer files; CC BY-NC-SA 4.0 - never in the repo) by hand to
  data\models\finbert\; pin HF commit + sha256 per file; local_files_only; torch/transformers in
  requirements-scorer.txt, not requirements.txt (CI unchanged); raw 3-class probabilities stored, never flipped;
  several companies in one headline = uncertain; filing-vs-headline disagreement recorded as conflict; scores of
  headlines before the model's training cutoff refused for replay; ADR-014.
- After 12B the owner chooses: BusinessLine/The Hindu RSS + RBI press-release RSS (approved 09-Nov; conditions in
  data\handover\STAGE12_BRIEF.md) or 40B step 12. Proposed, not approved: NSE PIT/SAST/pledge/bulk-deal CSVs.
- Owner to do: daily `fetch-gkg` and the feeds (section 5); send NSE research request (`data\handover\nse_request\`)
  and NSDL email (`data\handover\nsdl_request\email_to_nsdl.txt`); save any publisher replies (Moneycontrol, Mint,
  Business Standard, ET - asked 09-Nov) in data\handover\research\permissions\; December: NSE 2027 holiday list.
- Decisions pending: 30-company coverage cohort (3A.2 rule 5, preregistered) - also decides which companies get
  news names; price history for step 6a (NSE research data, else an authorised vendor with owner approval - the
  true bottleneck: 6 trading days of prices - 20/21-Aug, 21/22-Sep, 30-Sep, 01-Oct-2026; the liquidity band
  ignores sessions older than 120 days, so from 20-Dec-2026 sentiment is refused for every company unless at
  least 5 newer bhavcopies are loaded by hand).
- Remaining 40B order after 12: 12 Feature Factory, 13 Target Engine, 14 Research Agent v0.1 (evidence selection
  30A.1 and supporting/contradictory/missing sets 30A.2 build on the hub), 15 Prediction Ledger, 16 Shadow,
  17-23. Steps 13-16 are the critical path (3F); 6a runs alongside.
- Factors still missing (the hub names the domains; these are inside built domains): derivatives positioning
  (3D, no licensed source), CPI food inflation (narrower filter), CPI base 2012, WPI (DPIIT terms), India VIX
  and Nifty (NSE request), GDELT topic searches for geopolitics, adjusted prices as evidence.

## 9. Where details live (read only when needed)
- Architecture line ranges in docs/Master_Architecture_v2_2_0_FROZEN.md: 3B 392-429, 3C 432-461, 3G 491-536,
  3F 590-636, 4 669-755, 4D 757-798, 4F 800-843, 4C 845-889, 4E 891-914, 4A 916-984, 4B 986-1089, 4G 1091-1121,
  5A 1146-1191, 5B 1193-1241, 5C 1243-1264, 7A 1531-1577, 9A 1640-1662, 9B 1663-1701, 9C 1703-1774,
  10 1835-1887, 11 1888-1922, 14A 2040-2075, 16-18 2098-2168, 21 2212-2316, 29 2771-2795, 30A 2812-2855,
  34 3190-3245, 35A 3265-3402, 37 3460-3490, 40B 3660-3703, 40D 3765-3829, 46 4104-4164, 47 4165-4274,
  47A 4276-4302.
- Per stage: `stages/STAGE_*_acceptance.yaml`, `docs/decisions/ADR-*.md`, module docstrings.
- Research notes: `data\handover\research\` (flows_terms_2026-10-04.md, github_survey, samples per source).
