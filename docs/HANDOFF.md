# HANDOFF (compact) - AI Self-Learning Equity Research Agent

Compact handoff written 2026-10-05 (end of the fifth chat: hand-over tools, Stage 11). Read THIS file fully;
read other files only when a task needs them (section 9 says where). Governing architecture:
`docs/Master_Architecture_v2_2_0_FROZEN.md` (v2.2.0, frozen - amend only by insertion with an ADR, 46/46A).
Older detail is in git history: `git show 6cdf2fe:docs/HANDOFF.md` (long handoff up to Stage 10D).

## 0. State (05-Oct-2026)
| Item | State |
|---|---|
| Last pushed commit | Stage 11 Knowledge/Event Hub (ADR-012), committed by `stage.py commit stage11` - see `git log -1`. Before it: `2994320` Stage 10E. 957 tests. |
| Stage 11 | ACCEPTED: check PASS (957 tests, 24/24 faults, smoke on a database copy), install PASS 05-Oct 22:43, live `show-evidence HDFCBANK` verified (record in stages/STAGE_11_acceptance.yaml). |
| Database | `data/equity.sqlite`, schema 20 (Stage 11 adds no migration), 19 sources. Backups `data/equity_before_*.sqlite` (latest `_11`). |
| First check each chat | `python data\handover\tools\status.py --ci` (one screen: git, tests, stage report, database, freshness, gaps, calendar, Downloads, CI). |
| Next build | Stage 12 = Sentiment Adapter (40B step 10) - owner's choice 05-Oct ("hub first, then sentiment, then choose"). Needs news data: the owner should run `fetch-news` daily from now. |

### 0.1 Verify Stage 11 at the start of the next chat
`python data\handover\tools\status.py --ci` must show: HEAD = the Stage 11 commit, tree clean, origin/main
equal, tests 957 passed, CI success for HEAD. If `git log -1` is still Stage 10E, the owner had not finished:
`python data\handover\stage11\patch_stage11_record.py`, then `python data\handover\tools\stage.py commit stage11`.
status.py fixed 05-Oct after the install: it counts untracked files by their '??' lines.

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
3. Only `src/ingestion/news_fetch.py` opens network connections (static tests), allow-list of 7 hosts, exact
   paths, no redirects: api.gdeltproject.org, www.sebi.gov.in (/sebirss.xml), api.stlouisfed.org (series,
   observations, release/dates), api.mospi.gov.in (3 paths), www.federalreserve.gov (/feeds/press_monetary.xml),
   www.ecb.europa.eu (/rss/press.html), www.boj.or.jp (/en/rss/whatsnew.xml). New host = owner approval + ADR.
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
12. RBI not used (terms). Commercial Indian news sites not sources. NSDL and CDSL FPI data not stored (terms).
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
- Owner's daily routine: `fetch-sebi` (feed keeps ~3 working days - daily!), `fetch-news`, `fetch-macro`,
  `fetch-india`, `fetch-events`; trading evenings: download both CSVs from https://www.nseindia.com/reports/fii-dii
  then `ingest-inbox`. Calendars (config/market_calendars.yaml) end 2026-12-31: regenerate before (xcal venv in
  `%TEMP%\xcal`, tools make_calendar_yaml.py; show-macro and status.py warn 60 days before).

## 6. Stages done (records in stages/*_acceptance.yaml, decisions in docs/decisions/ADR-001..012)
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
| 11 | (section 0.1) | 11 | Knowledge/Event Hub: one evidence object, read-only, gaps always said |
Tests: 957 after Stage 11. Fault checks: 10 32/32, 10B 21/21, 10C 63/63, 10C-2 58/58, 10D 101/101, 10E 31/31,
11 24/24.

## 7. Code map (src/)
- core: config, database (migrate/rollback/run_in_transaction), dates (strict_iso_date), sessions (time zones),
  calendars (XNYS/XTKS/XBOM, CalendarError outside coverage), status (acceptance records), logging_setup.
- data_quality: missing_data (MissingClass), trust_chain (NoDataError), extraction_confidence.
- provenance: availability (disposition, PitClaim, parse_timestamp, price_availability), raw_store, pit_store
  (fact_as_of).
- universe: entities (resolve by ISIN/alias, validate_isin), equity_list, historical_universe, identity_bridges.
- ingestion: source_registry, market_adapters, corporate_actions/nse_corporate_actions, nse_financial_results,
  nse_announcements (events), intake, gdelt_news (stories), sebi_releases (releases), macro_context (FRED
  observations/latest), india_macro (MoSPI), macro_events (macro_events, scheduled_releases), event_routes
  (attribute, events_for), nse_flows (flows, missing_days), news_fetch (the ONLY network code).
- knowledge (Stage 11): evidence (Domain, Attribution, GapNature, Evidence, EvidenceGap, Bundle), hub (gather,
  clamp_window; adapters per domain; NOT_BUILT domains).
- features/price_series.py. Empty packages for later steps: abstention, calibration, experiments, ledger, models,
  regimes, research, targets, validation.
- manage.py commands: init-db, sources, load-*, ingest-prices, ingest-inbox, checklist, compare-series,
  bridge-isins, show-fundamentals/-events/-news/-sebi/-macro/-india/-macro-events/-flows/-evidence,
  fetch-news/-sebi/-macro/-india/-events, report.
- config: sources.yaml (19), news_names.yaml, macro_series.yaml (25), india_macro_series.yaml (9),
  market_calendars.yaml, declared_events.yaml and event_routes.yaml (owner-owned, empty).

## 8. Next steps and open items
- Stage 12 = Sentiment Adapter (40B step 10; architecture 4B 986-1089, 9A 1640-1662): sentiment-eligible stories
  only, one story one vote, below the liquidity threshold refused not down-weighted (4B.2), polarity is not
  issuer impact (4B.5). It plugs into the hub as Domain.PUBLIC_SENTIMENT (remove it from NOT_BUILT). Source
  options need terms research first: GDELT tone (another GDELT path = owner approval + ADR) or Alpha Vantage
  news sentiment (owner's key ALPHAVANTAGE_API_KEY; probe `data\handover\tools\av_probe.py`). Data first: the
  owner's first live `fetch-news` (nw_responses still 0), then daily.
- Owner to do: send NSE research request (`data\handover\nse_request\`), send NSDL email
  (`data\handover\nsdl_request\email_to_nsdl.txt`), start daily `fetch-news`.
- Decisions pending: 30-company coverage cohort (3A.2 rule 5, preregistered); price history for step 6a (NSE
  research data, else an authorised vendor with owner approval - the true bottleneck: 6 trading days of prices).
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
