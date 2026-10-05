# HANDOFF (compact) - AI Self-Learning Equity Research Agent

Compact handoff written 2026-10-05 (end of the fourth chat: Stages 10D and 10E). Read THIS file fully; read
other files only when a task needs them (section 9 says where). Governing architecture:
`docs/Master_Architecture_v2_2_0_FROZEN.md` (v2.2.0, frozen - amend only by insertion with an ADR, 46/46A).
The long handoff with every earlier detail is in git history: `git show 6cdf2fe:docs/HANDOFF.md`.

## 0. State (05-Oct-2026)
| Item | State |
|---|---|
| Last pushed commit | `6cdf2fe` Stage 10D (macro events, ADR-010). CI green. 898 tests. |
| Working tree | Stage 10E INSTALLED, NOT COMMITTED: 6 new + 4 patched files, all equal the tested copies (`data/handover/stage10e/work/repo`). 936 tests passed on the owner's computer. |
| Database | `data/equity.sqlite`, schema 20, 19 sources. Backups: `data/equity_before_10e.sqlite`, `_10d`, `_10c2`, `_10c`. |
| 10E live run | VERIFIED 04-Oct 23:39 IST: NSE 01-Oct FII/FPI net -9,159.99, DII 9,633.63; combined -9,484.22 / 10,041.84 (Rs crore). |
| Owner's Downloads | holds 05-Oct FII/DII files (NSE FII -4,092.96, DII 4,878.16) - not ingested yet: `python manage.py ingest-inbox` |
| Pending decision | the token-saving workflow (section 2) - owner asked for it; build its tools first in the next chat if approved. |
| Next build | after the tools: 40B step 10 (Sentiment, Stage 11) or step 11 (Knowledge/Event Hub) - ask the owner (section 8). |

### 0.1 Finish Stage 10E (owner runs, one block at a time, venv active: `.venv\Scripts\Activate.ps1`)
```powershell
python data\handover\stage10e\patch_stage10e_record.py
Copy-Item data\handover\HANDOFF_new.md docs\HANDOFF.md
python -m pytest -q > test_output.txt 2>&1; Get-Content test_output.txt -Tail 1
git add src tests migrations config stages docs manage.py README.md
git commit -m "Stage 10E: aggregate investor flows (ADR-011) - NSE's daily FII/FPI and DII files by hand download, known from ingestion never from the trade date, refused whole on any broken check, missing trading days reported never filled; NSDL and CDSL not used (terms)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```
Expected: `patched stages/STAGE_10E_acceptance.yaml`; `936 passed`. Verify after "done": `git log --oneline -2`,
`git status --short` empty, `git rev-parse HEAD origin/main` equal, test_output.txt (UTF-16) last line, CI:
`curl -s "https://api.github.com/repos/nalin17/ai-equity-agent/actions/runs?per_page=1"`.

## 1. Owner and working style
- Owner (GitHub nalin17) is NOT a developer: pastes PowerShell blocks, replies "done". Plain language, they/them.
  Windows 11, PowerShell 5.1 (no `&&`), Python 3.14, venv `.venv`. Never ask for Administrator.
- Owner decides policy (new source/host, paid data, architecture): ask with AskUserQuestion, recommended first.
  Technical judgement is delegated: "robust", fail-closed. Cross-verify facts from primary sources.
- Goal: personal BUY/HOLD/SELL with calibrated return ranges per horizon, learning over time; research for own
  decisions only, never distributed as advice. Honest message: nothing predicts until years of price history.
- Owner sends emails and downloads files; the assistant never does. Keys only in the owner's environment.
- Usage limits are tight: keep chats short (one stage per chat), outputs small, restartable work under
  `data\handover\` (git-ignored). The owner asked (05-Oct) to cut token use - see section 2.

## 2. Token-saving workflow (PROPOSED 05-Oct, owner to confirm)
1. One stage per chat; this compact handoff is the only required read; architecture read by line range (s.9).
2. `data\handover\tools\inspect.py <file|folder>` (to build): prints a <=60-line profile of any downloaded
   file - encoding/BOM, delimiter, header (normalised), rows, per column type/empties/distinct/min/max/top
   values, date and number formats, 3 sample rows; JSON/XML key trees. The owner runs it on new data and the
   assistant designs from the profile instead of reading raw files.
3. `data\handover\tools\stage.py` (to build): `check <stage>` copies the repo (git ls-files) to a temp sandbox,
   installs `data\handover\<stage>\files` + runs `patch_<stage>.py`, runs pytest (optionally `--faults`), and
   writes `data\handover\<stage>\report.txt` (<=40 lines: counts, first failure's last lines, file hashes).
   `install <stage>` does the real install: DB backup, copy files, patch, tests, init-db, report. The assistant
   writes code + tests once and reads only report.txt; the owner pastes errors if any.
4. `data\handover\tools\status.py` (to build): one-screen project status (git, last tests, schema, sources,
   row counts, last fetch per source, missing flow days, calendar end) - replaces multi-command verification.
5. Keep: tests with every change (CI and 40D need them), terms-first research, owner approvals. Light fault
   checks only for each stage's key rules. Drop: in-chat rehearsals and repeated verification.

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
11. An event without an issuer reaches a security only through a declared, recorded route (config/event_routes.yaml).
12. RBI not used (terms). Commercial Indian news sites not sources. NSDL and CDSL FPI data not stored (terms).
13. Static rules: `date.fromisoformat` only in core/dates.py; MissingClass and ExtractionConfidence values never as
   string literals elsewhere; bare token REVIEW banned; env reads only in news_fetch.py.

## 4. Method per stage (shortened)
Research real data + terms first (owner approves sources/samples) -> build in `data\handover\<stage>\work\repo`
(copy of tracked files, LF) -> tests -> light fault checks (`data\handover\tools\mutate_stage*.py <root>`) ->
real data on a DB copy (`tools\smoke_*.py <root>`) -> hand-over: new files in `data\handover\<stage>\files\`
(PowerShell copy loop that never overwrites), edits via `patch_<stage>.py` generated by
`tools\make_patch.py <owner repo> <tested repo> <out> <title> <files...>` (checks anchors, CRLF, second run STOPs)
-> owner installs, runs live -> `patch_<stage>_record.py` moves "first live run" to proven -> commit/push by owner.
Files handed over: pure ASCII (use chr() for non-ASCII), no line starting with `'@`.
Commit messages end with `-m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`;
`git add src tests migrations config stages docs manage.py README.md` (never data/).
Pitfalls: Bash heredocs and tool strings mangle backslashes - write scripts with the Write tool; Python
read_text() turns CR into LF; test_output.txt is UTF-16; fault scripts must restore bytes (write_bytes).

## 5. Project facts
- Folder `C:\Users\nalin\Projects\ai-equity-agent`; GitHub https://github.com/nalin17/ai-equity-agent (PUBLIC).
- SQLite (ADR-001); pytest (pytest.ini: pythonpath src); CI `.github/workflows/tests.yml` (Linux, Py 3.14);
  requirements: pytest, pyyaml only; network via stdlib urllib only.
- Logs `logs/app.log`; downloads land in `C:\Users\nalin\Downloads`, ingest-inbox moves them to `data\inbox`.
- Owner's daily routine: `fetch-sebi` (feed keeps ~3 working days - daily!), `fetch-news`, `fetch-macro`,
  `fetch-india`, `fetch-events`; trading evenings: download both CSVs from https://www.nseindia.com/reports/fii-dii
  then `ingest-inbox`. Calendars (config/market_calendars.yaml) end 2026-12-31: regenerate before (xcal venv in
  `%TEMP%\xcal`, tools make_calendar_yaml.py; show-macro warns 60 days before).

## 6. Stages done (all ACCEPTED, records in stages/*_acceptance.yaml, decisions in docs/decisions/ADR-001..011)
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
| 10E | (commit 0.1) | 9c | NSE FII/DII daily flows by hand download |
Tests: 936. Fault checks: 10 32/32, 10B 21/21, 10C 63/63, 10C-2 58/58, 10D 101/101, 10E 31/31.

## 7. Code map (src/)
- core: config, database (migrate/rollback/run_in_transaction), dates (strict_iso_date), sessions (time zones),
  calendars (XNYS/XTKS/XBOM, CalendarError outside coverage), status (acceptance records), logging_setup.
- data_quality: missing_data (MissingClass), trust_chain (NoDataError), extraction_confidence.
- provenance: availability (disposition, PitClaim, parse_timestamp), raw_store (sha256, duplicates refused), pit_store.
- universe: entities (resolve by ISIN/alias), equity_list, historical_universe, identity_bridges.
- ingestion: source_registry, market_adapters (read_raw_table), corporate_actions/nse_corporate_actions,
  nse_financial_results, nse_announcements (events, 4A.0 company types), intake (ingest-inbox kinds incl. flows),
  gdelt_news, sebi_releases, macro_context (FRED), india_macro (MoSPI), macro_events (feeds, me-types-1,
  me-dedup-1, calendar, derived releases, declared events), event_routes (read-across routes, attribute),
  nse_flows (FII/DII), news_fetch (the ONLY network code).
- features/price_series.py. Empty packages for later steps: abstention, calibration, experiments, ledger, models,
  regimes, research, targets, validation.
- manage.py commands: init-db, sources, load-*, ingest-prices, ingest-inbox, checklist, compare-series,
  bridge-isins, show-fundamentals/-events/-news/-sebi/-macro/-india/-macro-events/-flows, fetch-news/-sebi/
  -macro/-india/-events, report.
- config: sources.yaml (19), news_names.yaml, macro_series.yaml (25), india_macro_series.yaml (9),
  market_calendars.yaml, declared_events.yaml and event_routes.yaml (owner-owned, empty).

## 8. Next steps and open items
- Owner to do: send NSE research request (`data\handover\nse_request\`), send NSDL email
  (`data\handover\nsdl_request\email_to_nsdl.txt`), first live `fetch-news` (GDELT; nw_responses still 0),
  optional Alpha Vantage probe (`data\handover\tools\av_probe.py`, key ALPHAVANTAGE_API_KEY) for sentiment.
- Decisions pending: token-saving tools (s.2); 30-company coverage cohort (3A.2 rule 5, preregistered);
  price history for step 6a (NSE research data, else an authorised vendor with owner approval - the true
  bottleneck: only ~8 trading days of prices exist).
- Remaining 40B order: 10 Sentiment, 11 Knowledge/Event Hub, 12 Feature Factory, 13 Target Engine, 14 Research
  Agent v0.1, 15 Prediction Ledger, 16 Shadow operation, 17-23 learning, calibration, API. Steps 13-16 are the
  critical path (3F); 6a runs alongside.
- Owed: CPI food inflation (narrower filter), CPI base 2012, WPI (DPIIT terms), India VIX/Nifty (NSE request),
  GDELT topic searches for geopolitics (after a successful fetch-news), calendars before 2026-12-31.

## 9. Where details live (read only when needed)
- Architecture line ranges in docs/Master_Architecture_v2_2_0_FROZEN.md: 3C 432-461, 3G 491-536, 3F 590-636,
  4 669-755, 4D 757-798, 4F 800-843, 4C 845-889, 4E 891-914, 4A 916-984, 4B 986-1089, 4G 1091-1121,
  5A 1146-1191, 5B 1193-1241, 5C 1243-1264, 7A 1531-1577, 9A 1640-1662, 9B 1663-1701, 9C 1703-1774,
  10 1835-1887, 11 1888-1922, 14A 2040-2075, 16-18 2098-2168, 21 2212-2316, 29 2771-2795, 34 3190-3245,
  35A 3265-3402, 37 3460-3490, 40B 3660-3703, 40D 3765-3829, 46 4104-4164, 47 4165-4274, 47A 4276-4302.
- Per stage: `stages/STAGE_*_acceptance.yaml` (proven / not_claimed / negative assertions), `docs/decisions/ADR-*.md`,
  module docstrings (each lists the real-data rules it follows).
- Research notes: `data\handover\research\` (flows_terms_2026-10-04.md, github_survey, samples per source).
- Full earlier handoff (stage-by-stage detail, NSE file quirks, news rules): `git show 6cdf2fe:docs/HANDOFF.md`.
