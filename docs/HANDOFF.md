# HANDOFF - AI Self-Learning Equity Research Agent

Rewritten 2026-10-04 at the end of the third long build chat (Stages 10C and 10C-2), so
that a new chat can continue without losing anything. Read this WHOLE file before doing
anything else. It replaces the 2026-10-03 handoff and keeps everything that was in it.
The governing architecture is `docs/Master_Architecture_v2_2_0_FROZEN.md` (v2.2.0).

---

## 0. Read first - exact state at the end of the third chat (04-Oct-2026, about 18:30 India time)

| Item | State |
|---|---|
| Last pushed commit | `36450db` Stage 10C (FRED/ALFRED macro context, ADR-008). CI green. 632 tests. |
| Working tree (NOT committed yet) | Stage 10C-2 installed by the owner: 10 new files + 6 patched files. All 16 were checked byte for byte (new files) and with `diff --strip-trailing-cr` (patched files) against the tested copies: identical. |
| Tests on the owner's computer | `740 passed` (test_output.txt, 04-Oct 17:58) |
| Database | `data/equity.sqlite`, schema version 18 (migrations 0001-0018). Backup before 10C-2: `data/equity_before_10c2.sqlite`; before 10C: `data/equity_before_10c.sqlite`. |
| First live fetch-india | Done by the owner 04-Oct-2026 17:59 India time and VERIFIED: 9 series, 15 requests, 5 reads of 15 pages, 461 values, 24 blank year-on-year rates counted, 0 refused, 0 problems - identical to the tested copy. |
| Acceptance record update | Script ready and tested (twice, second run STOPs): `data\handover\stage10c2\patch_stage10c2_record.py`. NOT run yet. |
| This handoff | `data\handover\HANDOFF_new.md`; it becomes `docs\HANDOFF.md` in the 10C-2 commit (section 0.1). |
| Next build | Stage 10D = architecture 40B step 9b, Macro and Geopolitical Events (section 14). |

If `git log -1` still shows `36450db`, the Stage 10C-2 commit has NOT been made yet: do
section 0.1 first. If it shows a "Stage 10C-2" commit, verify it (section 0.1, "After done").

### 0.1 Finishing Stage 10C-2 (owner commands; the assistant only verifies)

The owner runs, in PowerShell from the project folder with the venv active
(`.venv\Scripts\Activate.ps1`), one block at a time:

```powershell
python data\handover\stage10c2\patch_stage10c2_record.py
```
Expected: `patched stages/STAGE_10C2_acceptance.yaml` (a second run prints `STOP: the live
run is already recorded. Nothing was changed.`). It removes the not_claimed line "first
live fetch-india run by the owner (verified after this commit)" and adds two proven lines
with the live numbers.

```powershell
Copy-Item data\handover\HANDOFF_new.md docs\HANDOFF.md
```
(Overwrites the tracked handoff with this file - git keeps the old one.)

```powershell
python -m pytest -q > test_output.txt 2>&1; Get-Content test_output.txt -Tail 1
```
Expected: `740 passed` (test_architecture_baseline requires docs/HANDOFF.md and README.md
to contain the text `Master_Architecture_v2_2_0_FROZEN.md` - this file does).

```powershell
git add src tests migrations config stages docs manage.py README.md
git commit -m "Stage 10C-2: India macro statistics from MoSPI eSankhyiki and market calendars (ADR-009) - CPI, IIP and GDP as current-decision context from the first read; New York, Tokyo and NSE/BSE calendars set aside closes repeated on closed days; legacy TLS for MoSPI only, certificates always checked" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

After the owner replies "done", verify (method section 5 step 7):
- `git log --oneline -2`, `git status --short` (must be empty; `data/` and
  test_output.txt are ignored), HEAD equals origin/main (`git rev-parse HEAD origin/main`).
- `test_output.txt` last line (it is UTF-16 - decode as UTF-16): 740 passed.
- Committed files equal the tested copies: new files in
  `data\handover\stage10c2\files\` (cmp), patched files equal what is on disk now; the
  acceptance record has the two new "first live fetch-india" lines and no longer the
  not_claimed line; docs/HANDOFF.md equals data/handover/HANDOFF_new.md
  (`diff -q --strip-trailing-cr`).
- CI: `curl -s "https://api.github.com/repos/nalin17/ai-equity-agent/actions/runs?per_page=2"`
  (status completed, conclusion success, head_sha = the new commit).
- Then offer to delete the 143 MB scratch environment `C:\Users\nalin\AppData\Local\Temp\xcal`
  (exchange_calendars 4.13.2 for regenerating calendars - the owner was told it would be
  deleted after the commit unless they want it kept; it can be recreated in 2 minutes:
  `python -m venv xcal` then `xcal\Scripts\pip install exchange_calendars==4.13.2`, with
  the owner's permission, because pip downloads files).

### 0.2 Things the owner still has to do

1. Send the NSE research-data request (section 13.6): fill the official form with the
   answers in `data\handover\nse_request\1_form_answers.txt` (tick mark U+2713 where the
   form asks for a tick), sign it, attach it to the email drafted in
   `data\handover\nse_request\2_email_to_nseri.txt`, send it to nseri@nse.co.in from their
   own mail. The assistant never sends it. Reply expected in weeks; refusal possible
   (eligibility text says accredited academic institutions; the owner has no academic
   link and applies as an independent researcher).
2. Daily routine from now on (in this order is fine):
   `python manage.py fetch-sebi` (at least once a day - SEBI's feed holds only about three
   working days; LAST READ WAS 03-Oct-2026 15:06 India time, so run it on Monday 05-Oct at
   the latest), `python manage.py fetch-news`, `python manage.py fetch-macro`,
   `python manage.py fetch-india`.
3. The first live `fetch-news` (GDELT) is STILL outstanding: nw_responses = 0. Run
   `python manage.py fetch-news` then `python manage.py show-news HDFCBANK`; if it ends
   "NOT FETCHED - GDELT refused", nothing is wrong; try again hours later. Reply "fetched"
   so the assistant can verify (section 9.6).
4. Optional, for Stage 11 sentiment: the Alpha Vantage probe (section 13.3).
5. Open decisions (the assistant raises them at the right stage): the 30-company coverage
   cohort is NOT chosen (architecture 3A.2 rule 5: rule mechanical, preregistered, dated);
   price history for step 6a (NSE research request first; an authorised paid vendor if too
   slow - each paid source needs the owner's approval with its price and terms; the owner
   said they are willing to pay where needed).

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
  UTF-16 (a plain `tail -1` shows spaced-out characters or a blank line).
- The owner delegates judgement: "whatever you feel is right and best suited to make
  the model robust". Prefer robustness and fail-closed behaviour over coverage. For
  decisions that change policy (new network access, new source, paid plan, architecture)
  the assistant asks first - the AskUserQuestion tool worked well for this.
- The owner asks the assistant to cross-verify facts ("just cross verify again") - check
  the primary source and quote it, do not answer from memory.
- The owner's goal, in their words (03-Oct-2026): build it "like an big institutional
  level model for my personal recommendation"; the model "should be able to predict
  which stock to buy, hold or sell and what could be the percentage gain by holding that
  very stock for x number of days or months, and it should keep on getting better by
  learning all the factors that can influence its growth or downfall" - including global
  news, technical and fundamental factors, oil, wars, China, Japan, US markets, bonds,
  Treasury news, and sovereign and other ratings. Architecture v2.2.0 (ADR-007) is the
  answer: see section 12.
- On data: the owner asked for APIs instead of hand downloads where legal, and set the
  rule "first check the free option, if not we will buy the premium plan". On 03-Oct-2026
  they added: "Whatever we are sure of lets take it from repo and rest as and when
  required will take API, even if we have to purchase it" and then chose LICENSED ONLY
  (section 13.5). The assistant must say in advance which stage needs which key from
  which source - free options first.
- Never ask them to run PowerShell as Administrator (it once broke the pytest cache).
- They have a separate project (C:\Users\nalin\Documents\Stock-Analysis-Agent, repo
  nalin17/ai-self-learning-equity-research). Do NOT reuse it: ADR-002 (independent build).
- At the end of a long chat the owner asks for a handover file like this one.
- Usage limits: the chat can stop mid-task ("I hit my usage limit ... Please continue from
  where you left off"). Keep work restartable: everything that must survive goes under
  `data\handover\`, never only in the session scratchpad.

## 2. Project facts

| Item | Value |
|---|---|
| Project folder | C:\Users\nalin\Projects\ai-equity-agent |
| GitHub | https://github.com/nalin17/ai-equity-agent (PUBLIC - never commit secrets, API keys or data) |
| OS / Python | Windows 11 Home, Windows PowerShell 5.1, Python 3.14, venv at `.venv` (activate: `.venv\Scripts\Activate.ps1`) |
| Database | SQLite at `data/equity.sqlite` (ADR-001: DuckDB is blocked by Windows Smart App Control - never suggest disabling it) |
| Tests | pytest; `pytest.ini`: pythonpath = src, testpaths = tests, addopts = -p no:cacheprovider |
| CI | `.github/workflows/tests.yml`, Python 3.14, runs pytest on every push (Linux) |
| Dependencies | requirements.txt: pytest, pyyaml (nothing else); network code uses only the standard library (urllib, ssl). exchange_calendars is NOT a dependency - it only generated config/market_calendars.yaml |
| Internet use by the program | only `src/ingestion/news_fetch.py`, allow-list of 4 hosts: api.gdeltproject.org (fetch-news, ADR-005), www.sebi.gov.in (only /sebirss.xml, fetch-sebi, ADR-006), api.stlouisfed.org (fetch-macro, ADR-008), api.mospi.gov.in (fetch-india, ADR-009). Everything else is hand downloads |
| FRED key | Windows USER environment variable `FRED_API_KEY`, set by the owner in their own PowerShell; read only by news_fetch.py; never in chat, repo, DB, files, logs, URLs stored or errors |
| Git line endings | core.autocrlf=true; index is LF; working files are CRLF or mixed - fine |
| `.gitignore` | .venv/, __pycache__/, *.pyc, .pytest_cache/, .env, data/, *.duckdb, *.parquet, logs/, test_output.txt, git_status.txt |
| Log file | `logs/app.log` (every command logs there; the assistant reads it to verify runs) |
| Check CI | `curl -s "https://api.github.com/repos/nalin17/ai-equity-agent/actions/runs?per_page=2"` |
| Microsoft Edge | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` (version 154) - used headless to print the architecture PDF |
| Owner's temp folder | `C:\Users\nalin\AppData\Local\Temp` (`$env:TEMP`); `xcal\` there = exchange_calendars scratch venv |

## 3. Authority documents

- `docs/Master_Architecture_v2_2_0_FROZEN.md` - THE frozen architecture (v2.2.0,
  2026-10-03, ADR-007). It is v2.1.1 plus insertions only (303 lines added, 0 deleted,
  2 declared one-line replacements), which tests/test_architecture_baseline.py checks on
  every commit. The PDF copy `docs/Master_Architecture_v2_2_0_FROZEN.pdf` (81 pages) is
  generated from it and never edited (46A). The owner said of v2.1.1 "consider this as
  final freezed architect, we will stick to it" and of v2.2.0 "freeze it new final version
  that we have to follow". Section numbers in code and acceptance records (3G, 4, 4A, 4C,
  4C.1, 4G, 5A.1, 5B, 5C, 6C, 6D, 9B, 40B, 40D, 47, 47A ...) refer to it. Amend it only
  under section 46/46A: as insertions, with an ADR, a control audit, and the audit test
  kept green.
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
  - ADR-008 FRED/ALFRED macro context (Stage 10C): host api.stlouisfed.org, key from the
    environment, FRED notice.
  - ADR-009 MoSPI eSankhyiki India macro and market calendars (Stage 10C-2): 4th host
    api.mospi.gov.in with legacy TLS renegotiation for that host only; calendars generated
    from exchange_calendars (Apache-2.0, licence text in
    `docs/third_party/exchange_calendars-LICENSE.txt`).
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
   news_fetch.py may call only the 4 allowed hosts (section 2) and only their declared
   paths; it follows no redirects. Any new network source needs the owner's approval, an
   ADR, a terms check and a change to the allow-list and its tests (architecture 4G).
2. LICENSED ONLY (owner decision 03-Oct-2026): from GitHub/Hugging Face take only what the
   licences and the original data owners allow. Repositories that copy NSE data (bhavcopy
   mirrors, Nifty/India VIX histories, scraped datasets) are NOT used - not even after
   comparing them with our own files.
3. TradingView data is display-only (non-display/machine use prohibited) - not a source,
   also not when a vendor such as Alpha Vantage relays it (4G rule 8).
4. The assistant never downloads files without explicit permission (state file name,
   source and size when asking); reading a page in the browser to design code is fine.
   The owner downloads; the assistant reads files from `C:\Users\nalin\Downloads` or
   `data\inbox`. Research samples fetched with the owner's permission go to
   `data\handover\research\`. Navigating the browser pane to a URL that serves a file pops
   up a save dialog on the owner's screen - avoid it. `pip install` downloads files too:
   ask first.
5. Never ask for, display or store API keys or passwords in chat, in the repository, in
   logs, in stored URLs or in error messages (4G rule 5). Keys are typed by the owner
   into their own PowerShell or stored by them as a user environment variable.
6. Never repair source data silently; refuse, quarantine or mark missing with a reason
   (missing-data classes, 4C). Never fill a blank, never carry a value forward.
7. Everything is append-only (triggers on history tables); corrections are new versions
   (vintages).
8. Point in time (5B, 5C): use only what was knowable at the decision time; publication
   times must be proven (exchange dissemination time, our own retrieval, GDELT's first-seen
   time + 15 minutes, FRED's own last_updated read after the data) or the item is
   AVAILABILITY_REVIEW for historical replay. A foreign close never enters an Indian
   decision before that session ended (5C). A value on a day its market was closed is
   never used as a close.
9. Ingested text is data, never instruction (4D). Tests include injection-shaped text.
10. Commercial Indian news sites are not sources: Business Standard and HT/Mint terms
    forbid AI use (RSS included); Economic Times blocks automated reading. Never open
    article links from GDELT; never read article bodies. RBI is not used (ADR-006).
11. Never put real individuals' names or tax ids (they appear in SEBI titles) into tests
    or the public repository; use company names in fixtures.
12. Certificate checking is never switched off (a static test enforces it). Only
    api.mospi.gov.in gets `ssl.OP_LEGACY_SERVER_CONNECT`, nothing else.
13. Macro series are context only: never a covered security, target or benchmark (static
    tests: no target/benchmark/ledger/calibration/validation/model/universe module imports
    the macro context).

## 5. How each stage is built and handed over (follow exactly)

1. Research first on REAL data: read pages in the browser (read only; WebFetch is
   blocked by many Indian sites), check the source's terms (4G rule 1), then ask the owner
   for permission to fetch samples (state how many requests) or ask them to download
   specific files. Inspect real files before writing code (columns, quirks, identities,
   time stamps). Probe scripts that need a key read it from the environment and never
   print it (`tools\fred_probe.py` is the model).
2. Build in a scratch copy: `git ls-files | tar -cf - -T -` into a scratchpad folder,
   convert CRLF to LF there (`sed -i 's/\r$//'` on .py/.sql/.yaml/.md/.ini/.txt), copy the
   owner's real config files that are not tracked if needed, and run tests with the
   owner's venv interpreter, which already has pytest and pyyaml:
   `/c/Users/nalin/Projects/ai-equity-agent/.venv/Scripts/python.exe -m pytest -q`
   (the system Python has no pytest; nothing needs installing).
3. Deliberate-fault checks: a script mutates one line of the new code at a time and runs
   the stage tests; every fault must make a test fail. Files are restored byte for byte;
   every run goes through a dead proxy (HTTPS_PROXY to 127.0.0.1:9) so no fault can reach
   the internet. When one survives, add the missing test. When shared code changes, re-run
   the older stages' scripts too and update anchors that the new code duplicated or
   reshaped. Final counts: Stage 10 32/32, 10B 21/21, 10C 63/63, 10C-2 58/58. Scripts:
   `data\handover\tools\mutate_stage10*.py <scratch repo root>`.
4. Run the real data on a COPY of the owner's database (`cp data/equity.sqlite`), with
   copies of their downloads (never touch their Downloads folder), and record the real
   numbers in the acceptance record (`tools\smoke_*.py <scratch root>`).
5. Every file handed over is checked: pure ASCII (non-ASCII characters inside Python
   strings become `\uXXXX` escapes; in YAML use a double-quoted `"\u20b9"` escape), and no
   line starting with `'@` (that would end a PowerShell here-string).
6. Hand-over method:
   - New files: a folder of tested files under `data\handover\<stage>\files\` and one
     PowerShell loop that refuses to overwrite:
     ```powershell
     $src = "data\handover\stage10c2\files"; $root = (Resolve-Path $src).Path; Get-ChildItem $src -Recurse -File | ForEach-Object { $rel = $_.FullName.Substring($root.Length + 1); if (Test-Path $rel) { "ALREADY THERE: $rel" } else { New-Item -ItemType Directory -Force -Path (Split-Path $rel) | Out-Null; Copy-Item $_.FullName $rel; "copied $rel" } }
     ```
     A folder in the session scratchpad disappears when the chat ends - anything that
     must survive goes under `data\handover\` (git-ignored, persistent).
   - Edits to existing files: a checked Python patch script (`patch_*.py`, generated with
     difflib from the tested copy) that normalises CRLF, checks every anchor occurs exactly
     once AND that the new text is not already present, validates everything before
     writing anything, writes with `newline="\r\n"`, prints `patched <file>` per file and
     `PATCH COMPLETE`, or `STOP: ... Nothing was changed`. Test it on copies of the
     owner's real files first; check that the result equals the tested copy and that a
     second run STOPs.
   - Rehearse the owner's exact PowerShell steps with the PowerShell tool on a fresh copy
     of the repository in `$env:TEMP` (tracked files plus a copy of the DB), then
     compare every resulting file with the tested copies, then delete the rehearsal folder.
   - Then the owner runs: tests to `test_output.txt` with the expected last line; a DB
     backup (`Copy-Item data\equity.sqlite data\equity_before_<stage>.sqlite`);
     `python manage.py init-db` with the expected version and newly registered sources;
     the real-data commands with expected numbers; replies "done".
   - After the owner's first live run: verify it, then a small record patch
     (`patch_<stage>_record.py`) moves "first live run" from not_claimed to proven with the
     real numbers - before the commit (10C-2) or as its own commit (10C).
   - Commit messages end with `-m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`.
   - `git add src tests migrations config stages docs manage.py README.md` (never `data/`).
7. When the owner says "done": verify directly - `git log`, `git status`, HEAD equals
   origin/main, the last line of `test_output.txt` (UTF-16), `cmp` / `diff -q
   --strip-trailing-cr` of every changed file against the tested copy, read-only DB queries
   (`sqlite3.connect("file:data/equity.sqlite?mode=ro", uri=True)`; schema version is the
   table `schema_version`, sources are in `source_registry`), `logs/app.log`, and CI.
8. Tooling pitfalls learned:
   - The Write tool turns `\ufeff`, `\u00ae`, `\u20b9` and other `\uXXXX` escapes into
     real characters and `\b` into a backspace - after writing, re-escape (a small
     `to_ascii.py` / `tools\escape_tests.py`), or write a placeholder (e.g. RUPEE_SIGN) and
     replace it with a script; use `chr(0xFEFF)` in code.
   - Bash heredocs mangle backslashes (`\n`, `\u`) - write scripts with the Write tool.
   - A failed write or an illegal value can truncate a scratch file - keep the tested copy
     and restore from it; the owner's repository is only changed by the owner.
   - Python print of non-ASCII on this machine needs `PYTHONIOENCODING=utf-8`.
   - PowerShell 5.1: no `&&`; pass arguments to Start-Process as an array.
   - Static rules: `date.fromisoformat` only in `core/dates.py` (`strict_iso_date`);
     missing-data class names and extraction-confidence values are never string literals
     outside their home modules; the bare token REVIEW is banned in `src/`; network
     imports and environment reads only in news_fetch.py; no `investment_confidence`
     identifier in a module that touches extraction confidence; no code switches
     certificate checking off.
   - GDELT rate-limits hard: keep research requests few and minutes apart.
   - PDFs: there is no reportlab/poppler; render Markdown to HTML (`tools\md2html.py`) and
     print with headless Edge (`--headless=new --no-pdf-header-footer --print-to-pdf=...`).
   - Windows time zones: `[System.TimeZoneInfo]` in PowerShell was used to verify the
     hand-coded session rules (core/sessions.py) at 271,700 checkpoints.

## 6. Stage history (all ACCEPTED; all pushed except 10C-2; CI green)

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
| 10 | 6c2a2f7 | 40B step 9, 4A, 4B.4, ADR-005 | news headlines from GDELT; extraction confidence stored apart from investment confidence; rules nw-entity-1 and nw-dedup-1 |
| 10B | ac0633f | 40B step 9, 4A, 5B, ADR-006 | SEBI releases from its RSS feed; public only from the first read; companies by exact registered name (sb-entity-1); kinds from SEBI's sections (sb-kinds-1) |
| arch v2.2.0 | 9bb500f | 46, ADR-007 | architecture amended by insertion only; control audit test in CI; second handoff |
| 10C | 36450db | 40B step 9a, 3G, 4G, 5A.1, 5B, 5C, ADR-008 | 25 FRED/ALFRED series with session, time zone, publication time and vintages; a foreign close never reaches an Indian decision before its session ended; the FRED key stays on the owner's computer |
| 10C-2 | (to commit, section 0.1) | 40B step 9a, 4C, 4G, 5A.1, 5B, 5C, ADR-009 | India CPI/IIP/GDP from MoSPI (current decisions only); market calendars XNYS/XTKS/XBOM set aside closes repeated on closed days |

Acceptance records with exact claims, not-claimed items and negative assertions are in
`stages/STAGE_*_acceptance.yaml` (20 files after 10C-2; statuses such as
ACCEPTED_MACRO_CONTEXT_BASELINE for 10C and ACCEPTED_INDIA_MACRO_AND_CALENDARS_BASELINE
for 10C-2). `core/status.load_acceptance_records` checks them in the tests.

## 7. Current state (verified 2026-10-04)

- Tests: 393 at Stage 9; 482 after 10; 518 after 10B; 521 after v2.2.0; 632 after 10C;
  740 after 10C-2. Per file: architecture_baseline 3, stage01 5, stage02 19, stage03 47,
  stage04a 12, stage04b 27, stage05 30, stage06 31, stage07a 25, stage07b 38, stage07c 45,
  stage07d 15, stage08 23, stage08b 19, stage08c 10, stage08d 19, stage09 25, stage10 89,
  stage10b 36, stage10c_macro 111, stage10c2_india_calendars 108, static_rules 3.
- Schema version 18; migrations 0001-0018 (create source registry, entities,
  source_class, data_trust, pit_facts, historical_universe, market_adapters,
  corporate_actions, corporate_action_files, identity_bridges, financial_results,
  integrated_filings, revision_corrections, announcements, news, sebi_releases,
  macro_context, india_macro), each with up and down files.
- Sources registered (14): fred_alfred, gdelt_doc_news, market_calendars,
  mospi_esankhyiki, nse_announcements, nse_bhavcopy_equity, nse_corporate_actions,
  nse_equity_list, nse_financial_results_index, nse_financial_results_xbrl,
  nse_index_constituents, nse_integrated_filing_index, nse_integrated_filing_xbrl,
  sebi_rss.
- Data: 2,594 entities (from EQUITY_L) with 2,593 NSE-symbol aliases; 13,806 trusted
  daily prices over 6 trading dates (20-Aug to 01-Oct-2026 - far too short for any
  learning, see step 6a); 380 quarantine rows (history); 1,182 corporate actions; 1
  identity bridge (TAALTECH); results listings 5 (old page) + 49 (integrated); 17 results
  files loaded; 751 fundamental figures; 5,903 announcement filings forming 5,723 events;
  SEBI: 30 releases from 2 reads (03-Oct-2026 12:15 and 15:06 India time); GDELT news: 0
  (first fetch not run yet); FRED: 25 series, 68 responses, 59,971 vintages, 0 problems
  (first live run 03-Oct 22:01, second 42 minutes later stored nothing new; a run on
  04-Oct 17:56 found everything already present); MoSPI: 9 series, 5 reads, 15 pages,
  461 values, 0 problems (04-Oct 17:59).
- Historical-universe tables exist but hold no versions yet (universe_versions 0).
- `data/inbox` holds 32 files (all ingested); `data/fetched` holds the SEBI reads, FRED
  answers (fred_*.json) and MoSPI pages (15 files mospi_<dataset>_<key8>_<UTC stamp>_p<n>.json);
  `data/raw` holds every raw file by sha256; `data/checklist.html` is the download page.

## 8. Code map

- `manage.py` - commands: init-db, sources, load-equity-list FILE, ingest-prices FILE...,
  load-corporate-actions FILE, compare-series SYMBOL START END, bridge-isins,
  load-results-index FILE..., load-results FILE..., show-fundamentals SYMBOL [PERIOD_END],
  load-announcements FILE..., show-events SYMBOL [FROM] [TO],
  fetch-news [--symbols A,B] [--from DATE], show-news SYMBOL [FROM] [TO],
  fetch-sebi, show-sebi [--symbol SYMBOL] [FROM] [TO],
  fetch-macro [--series A,B] [--full], show-macro [SERIES] (warns when the market
  calendars end within 60 days), fetch-india [--series A,B], show-india [SERIES],
  ingest-inbox [--without-listing] [FOLDER], checklist [LISTING...] [--symbols A,B]
  [--since DATE] [--prices-from DATE], report (has lines for macro and "India macro (MoSPI)").
- `src/core/` - config, database (`connect`, `migrate`, `rollback`, `run_in_transaction`,
  `now_utc`), dates (`strict_iso_date`), logging_setup, status (2A vocabulary,
  `load_acceptance_records`; status must be a fixed status or ACCEPTED_<X>_BASELINE; every
  not_claimed and negative_assertions entry must be exactly false), sessions (Stage 10C:
  `ZONES` America/New_York with US daylight saving from 2007-03-11, Asia/Tokyo +9,
  Asia/Kolkata +5:30; `utc_offset(zone, day, clock)`, `local_to_utc(day, hhmm, zone)`;
  refuses times inside a changeover hour and US dates before 2007-03-11), calendars
  (Stage 10C-2: `Calendar.covers/is_session` - CalendarError outside coverage;
  `check_calendar`, `load_calendars(path)` -> (calendars, series_calendars), cached by
  file mtime).
- `src/data_quality/` - missing_data (`MissingClass`: not_applicable, not_yet_released,
  not_disclosed, extraction_failure, source_conflict, structurally_absent), trust_chain
  (`NoDataError` ...), extraction_confidence (`ExtractionConfidence`, 4A rule 4).
- `src/provenance/` - availability (`disposition(claim, decision_time, retrieved_at,
  published_at)`, `PitClaim.CURRENT_DECISION/HISTORICAL_REPLAY`, `Availability` ELIGIBLE /
  NOT_ELIGIBLE / AVAILABILITY_REVIEW, `parse_timestamp` - timezone mandatory), raw_store
  (`store_raw_artifact`, sha256 dedup - identical bytes raise ArtifactError), pit_store
  (`record_fact`, `record_correction`, `fact_as_of`).
- `src/universe/` - entities (`resolve(conn, identifier, as_of, alias_type=...)`),
  equity_list, historical_universe, identity_bridges.
- `src/ingestion/` - source_registry (REQUIRED_FIELDS, ALLOWED_VALUES incl. source class
  official_statistics and licensed_vendor; excluded classes private_tip_channel /
  unattributed_rumour / non_public_information; `sync_sources` never silently changes a
  registration), market_adapters, corporate_actions + nse_corporate_actions,
  nse_financial_results, intake, nse_announcements, gdelt_news (section 9), sebi_releases
  (9.7), macro_context (section 10), india_macro (section 11), news_fetch (the ONLY
  network code: GDELT Fetcher, `fetch_sebi`, `fred_key`, `FredClient`,
  `fetch_macro_series`, `MospiClient`, `fetch_india_request`, `tls_context(host)`,
  `http_get`, `_check_host`, `_NoRedirect`).
- `src/features/price_series.py` - raw/adjusted series.
- Empty packages reserved for later steps: abstention, calibration, experiments, ledger,
  models, regimes, research, targets, validation.
- `config/` - settings.yaml, sources.yaml (14 sources), news_names.yaml (9.2),
  macro_series.yaml (25 FRED series), india_macro_series.yaml (9 MoSPI series),
  market_calendars.yaml (3 calendars + series_calendars mapping).
- `stages/` - one acceptance record per stage. `docs/decisions/` - ADR-001..009.
  `docs/third_party/` - exchange_calendars licence.

## 9. Stage 10 (news from GDELT) and Stage 10B (SEBI) in detail

### 9.1 Why GDELT
Commercial Indian news sites forbid AI use or automated reading (rule 10). GDELT's terms:
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
- Tables (migration 0015): nw_responses, nw_articles (url UNIQUE, title verbatim, domain,
  language, source_country, seen_at, available_at), nw_retrievals, nw_problems,
  nw_extraction_runs, nw_extractions (role subject / mentioned / unassigned with CHECK
  constraints tying role and extraction_confidence). All append-only. No investment
  confidence anywhere (40B step 9 acceptance; static test).
- Story object (`stories(conn, decision_time, claim, isin)`): story_id, published_at,
  headline, language, copies, companies {isin: role, extraction_confidence, evidence},
  unassigned, searched_for, novelty {copies, sites, rule, repeats_an_exchange_filing:
  not_assessed}, source_quality {source, reliability_rating B, site_quality
  not_assessed}, event_type / direction / materiality / expected_horizon: not_assessed.
- GDELT fetcher: API https://api.gdeltproject.org/api/v2/doc/doc; query per company = its
  names as quoted phrases joined with OR (no country filter); mode artlist, format json,
  maxrecords 250, sort datedesc, startdatetime/enddatetime YYYYMMDDHHMMSS; USER_AGENT
  'ai-equity-agent/1.0 (personal research, non-commercial)'; no redirects; MIN_INTERVAL
  20 s; REFUSAL_WAITS 60, 180, 300 s, then RateLimited and nothing more that run
  (gave_up); a 250-article response is split in two until the window is under 2 hours;
  SEARCH_WINDOW 90 days; first fetch per company 7 days, later from the last stored window
  end minus 1 day; responses saved as data/fetched/gdelt_<SYMBOL>_<start>_<end>.json and
  kept as raw artifacts.

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
- Rule sb-kinds-1: enforcement/orders -> order, event type sebi_order;
  enforcement/recovery-proceedings -> recovery_proceeding; legal/circulars -> circular;
  media-and-notifications/press-releases -> press_release; anything else -> other.
- Rule sb-entity-1 (`NameReader`): a listed company is 'named' only when its registered
  name appears word for word (normalise_name: 'Ltd' = 'Limited', case and punctuation
  ignored; an apostrophe splits a word); names without a company suffix (PSU banks, LIC,
  GIC) must appear exactly as registered; longest name wins; a name shared by two
  registered companies links neither. Extraction confidence registered_name_in_title.
- Tables (migration 0016): sb_reads, sb_releases (link UNIQUE), sb_problems - append-only.
- `fetch_sebi`: only SEBI_FEED, refuses to send within 60 minutes of the last stored read,
  HTTP != 200 -> FetchError, checks the feed before writing data/fetched/sebi_<UTC>.xml.
- Real data 03-Oct-2026: 30 items, 30 stored, 0 refused; 16 orders, 12 recovery
  proceedings, 1 circular, 1 press release; companies named: SMC Global Securities and TV
  Vision; 'Adani Group Companies' and 'Lloyd Enterprises Limited' link nothing.

## 10. Stage 10C (FRED/ALFRED macro context, ADR-008) in detail - committed 36450db

- Owner decisions: FRED first, India next; approve FRED (ADR-008); the key lives in a
  Windows user environment variable `FRED_API_KEY`. During setup the owner saw a blank
  "key" output and could not get "FRED key OK"; it was solved with a diagnostic and an
  explanation (a user variable is seen only by PowerShell windows opened after it was
  set). Never print the key - only whether it is present.
- 25 series (config/macro_series.yaml, each with 3G group, region, kind market_close or
  published_statistic, market, calendar, time zone, session close for market closes,
  frequency, FRED units, licence note):
  rates_and_bonds DGS2, DGS10, T10Y2Y, DFF, ECBDFR, INDIRLTLT01STM (India 10Y, monthly),
  IRLTLT01JPM156N (Japan 10Y, monthly); currencies DEXINUS, DTWEXBGS, DEXCHUS, DEXJPUS;
  commodities DCOILBRENTEU, DCOILWTICO, DHHNGSP, PCOPPUSDM, PALUMUSDM; world equity
  NASDAQCOM, NIKKEI225; volatility and credit VIXCLS, VXEEMCLS, BAMLH0A0HYM2,
  BAMLEMCBPIOAS; US releases CPIAUCSL, PAYEMS, GDPC1. EXCLUDED_SERIES SP500, DJIA, DJCA,
  DJTA, DJUA (S&P Dow Jones Indices forbids reproduction; SP500 also has no ALFRED vintages).
- macro_context.py: `sync_series` (recorded once, never silently changed), `request_for`
  (daily series: rolling 3-year real-time window - FRED allows 2,000 vintage dates per
  answer, DGS10 has 5,122; monthly/quarterly: all vintages from 1776-07-04; LOOKBACK 45
  days daily, 90 weekly, 6 years monthly/quarterly; `--full` asks everything),
  `read_observations`, `read_series_meta`, `load_fred_answers`, `observations`, `latest`,
  `value_on`; `FRED_NOTICE` (printed by fetch-macro/show-macro and in README.md).
- Proof of availability: current decisions use this system's read; historical replay
  uses FRED's own `last_updated` read right AFTER the observations (proven = min(last
  updated, our read)); ALFRED vintage dates are kept but not used as proof. A market close
  is not available before its session close in its own zone converted to UTC.
- Missing values: a date FRED lists with "." is structurally absent; weekends of business
  day series structurally absent; later dates not yet released; nothing carried forward.
- Tables (migration 0017): mc_series, mc_responses, mc_vintages, mc_problems - append-only.
- Fetcher: only https://api.stlouisfed.org/fred/series/observations and /fred/series,
  observations first, FRED_INTERVAL 1 s, stops after HTTP 429; the key never reaches the
  DB, files, logs or messages (`_shown` masks it; an answer containing it is not stored).
- Real data: see stages/STAGE_10C_acceptance.yaml (first live run 03-Oct 22:01: 25/25
  series, 50 requests, 59,971 vintages over 50,190 dates 2006-01-01..2026-10-02, 1,624
  dates without a value, 0 refused, 0 conflicts; second run stored nothing new).
- Not claimed (10C): whether a "." date was a closed market or a late value; replay of
  values older than our first read; Shanghai, Hang Seng, EM index, GIFT Nifty, gold, steel;
  revisions older than the look-back unless --full; early-close times; macro exposure
  features and regime states; US release consensus/surprise.

## 11. Stage 10C-2 (MoSPI India macro + market calendars, ADR-009) in detail - installed, to commit

- Owner decisions (04-Oct-2026): no academic affiliation; MoSPI samples approved (~12
  requests); MoSPI approved as the 4th host (ADR-009) with legacy TLS for that host only;
  scope "Calendars + CPI/IIP/GDP" (WPI held; India VIX/Nifty wait for NSE).
- MoSPI eSankhyiki API: base https://api.mospi.gov.in, no key, paged JSON
  {data, meta_data (paging and totals), statusCode}. Paths used:
  cpi /api/cpi/getCPIData, iip /api/iip/getIipData, nas /api/nas/getNASData. Terms:
  MoSPI's own datasets are Category A under the Government Statistics Data Dissemination
  policy 2026 - reuse with prominent attribution ("Source: Ministry of Statistics and
  Programme Implementation (MoSPI), National Statistics Office - eSankhyiki", printed by
  fetch-india/show-india and in README.md). WPI belongs to the Office of the Economic
  Adviser (DPIIT) whose site publishes no reuse terms - not used. MoSPI's own sample code
  switches certificate checking off - NOT copied. The server needs TLS legacy
  renegotiation: `tls_context(host)` = `ssl.create_default_context()` plus
  `OP_LEGACY_SERVER_CONNECT` for api.mospi.gov.in only.
- 9 series in 5 requests (config/india_macro_series.yaml; each entry: series_id, dataset,
  request params, `expect` fields that every row must match, `select` fields that pick the
  aggregate row among breakdown rows, measure, unit, base, reconstructed flag):
  - CPI base 2024, Current (state 1 = All India, sector 3 = Combined, division 0 = General):
    IN_CPI24_GEN_INDEX, IN_CPI24_GEN_INFL (select group null).
  - CPI base 2024, Back series 2013-2024 (reconstructed by MoSPI on the new base; must be
    declared reconstructed): IN_CPI24B_GEN_INDEX, IN_CPI24B_GEN_INFL.
  - IIP base 2022-23 General (category 4, select sub_category ""): IN_IIP2223_GEN_INDEX,
    IN_IIP2223_GEN_GROWTH.
  - IIP Sectoral (category 2 = Manufacturing; 984 rows incl. 23 sub-industries):
    IN_IIP2223_MFG_INDEX.
  - NAS base 2022-23 quarterly, indicator 5 (GDP), expect unit "\u20b9 Crore" (YAML
    escape - keep the file ASCII): IN_GDP2223_Q_REAL, IN_GDP2223_Q_NOMINAL. Quarters are
    financial-year quarters: Q1 of FY 2026-27 is dated 2026-04-01.
  - Dropped: CPI food inflation (that request returns 44 pages; MAX_PAGES 20 refuses it) -
    needs a narrower filter.
- india_macro.py: SOURCE_ID mospi_esankhyiki; API_PATHS; PAGE_SIZE 100; MAX_PAGES 20;
  `check_entry`, `sync_india_series`, `india_series_info`, `registered_india_series`,
  `requests_to_fetch`, `page_params`, `read_page`, `period_of`, `_keep_page` (identical
  artifact reused; another source's identical file refused), `load_mospi_pages(conn,
  dataset, request, pages, raw_dir)`: totals checked across pages; any row breaking
  `expect` refuses the whole answer; a null measure (no year-on-year rate in a base's first
  year) is counted as values_not_given, never stored; problems period_conflict,
  row_refused, no_aggregate_row; a changed value is a new vintage; a read is dated by its
  LAST page's retrieval. `india_observations` (historical replay returns [] -
  AVAILABILITY_REVIEW, no publication time) and `india_latest` (status published or
  reconstructed).
- Tables (migration 0018): mo_series (with row_select), mo_reads, mo_pages, mo_values,
  mo_problems - append-only triggers.
- Fetcher: `MospiClient`, `fetch_india_request` - asks only the 3 paths, MOSPI_INTERVAL
  3 s, reads ALL pages and checks them before writing anything, refuses > 20 pages, stops
  after HTTP 429; files data/fetched/mospi_<dataset>_<key8>_<stamp>_p<n>.json (key8 =
  first 8 hex of sha256 of the sorted request JSON).
- Market calendars (core/calendars.py, config/market_calendars.yaml): generated from
  exchange_calendars 4.13.2 (Apache-2.0) for XNYS (New York, 197 closed weekdays), XTKS
  (Tokyo, 342) and XBOM (NSE/BSE, 306; weekend sessions 2024-01-20 and 2025-02-01),
  coverage 2006-01-01 to 2026-12-31; outside coverage CalendarError (never guessed).
  series_calendars: NASDAQCOM -> XNYS, NIKKEI225 -> XTKS. For mapped series (in
  macro_context `_calendar_for`, `_by_calendar`, `_known_at`, `value_on`): a value on a
  closed day becomes structurally absent (not used; the stored vintage stays as FRED gave
  it); no value on a trading day is a source conflict. NOT mapped on purpose: Treasury
  yields (bond-market calendar: closed Columbus and Veterans Day, open Good Friday) and VIX
  (Cboe computes it on some US holidays).
- Calendar checks on real data: NSE's official 2026 holiday list agrees 16 of 16; FRED's
  Nasdaq 2016-2026 agrees on 102 of 103 closed days, Nikkei 180 of 181 - the exceptions
  Good Friday 19-Apr-2019 and the Tokyo outage of 1-Oct-2020 carry the previous close
  repeated and are now set aside. On the owner's history (2,805 Nasdaq and 2,806 Nikkei
  dates) exactly those two closes are set aside and no trading day lacks a value.
- Regenerating calendars (before 2026-12-31; show-macro warns 60 days before): with the
  scratch venv `C:\Users\nalin\AppData\Local\Temp\xcal` run
  `data\handover\tools\make_calendar_yaml.py <output path>` (edit START/END), then
  `tools\check_calendars.py` and `tools\make_calendars.py` for the CSV research copies,
  then hand over the new config file as a normal stage change with tests.
- Tests 108 (tests/test_stage10c2_india_calendars.py); faults 58/58; acceptance record
  stages/STAGE_10C2_acceptance.yaml (status ACCEPTED_INDIA_MACRO_AND_CALENDARS_BASELINE;
  proven incl. real data; not_claimed: food inflation, WPI and RBI, CPI base 2012,
  India VIX and Nifty, MoSPI publication times, Cboe/US bond/Shanghai/Hong Kong
  calendars, calendars beyond 2026-12-31, early-close times; 9 negative assertions).
- Live values (04-Oct-2026): CPI Aug-2026 index 108.74, inflation 4.82; CPI back series to
  Dec-2024 102.90 / 5.22 (reconstructed); IIP Aug-2026 123.3, growth 8.0, manufacturing
  126.6; GDP Apr-Jun 2026 8,136,153 crore real and 8,826,871 crore nominal.

## 12. Architecture v2.2.0 (ADR-007) - what changed and why

The owner asked whether the model considers everything that moves Indian stocks and
whether it can give buy/hold/sell with expected percentage gains and keep improving. A
full re-read of v2.1.1 found: Sector/macro was Core (3B) but no 40B step built it; the
event types (4A.0) were company-level only; world markets were not named; no rule for
markets closing at different hours; return magnitudes were required in the ledger (21)
but never scored, and no rule mapped forecasts to BUY/HOLD/SELL; 40C described the
predecessor codebase. Changes (all insertions):

| ACR | Change | Section |
|---|---|---|
| 103 | Global and India macro context: rates and bonds, currencies, commodities, world equity markets, volatility and credit stress, economic releases (India CPI/WPI/IIP/GDP/GST/PMI, US CPI/payrolls/GDP, China), investor flows (FPI/FII, DII), monsoon, Budget, elections, MSCI/FTSE reviews. Context, never covered securities or benchmarks; two routes only (regime state, or measured company sensitivity) | 3B rule 4, new 3G |
| 104 | Cross-market timing: every series carries exchange, session calendar, time zone, publication time; available_at in UTC, never the calendar date; a closed foreign market is `structurally_absent`, never carried forward | new 5C |
| 105 | New event groups: monetary policy and rates; fiscal, trade and regulation; sovereign and macro data; geopolitics and shocks; index-provider and flow events. Rule 5: an event without an issuer reaches a security only by declared read-across, sector membership or measured sensitivity, recorded | 4A.0, 4A rule 5 |
| 106 | Macro exposure feature = measured company sensitivity x observed factor move, admitted as a Fundamental-family feature; raw macro levels stay routing-only | 9A, 9C |
| 107 | Regime engine: global risk appetite, US dollar and rates direction, commodity shock, foreign-flow state, geopolitical stress | 29 |
| 108 | New 40B steps before step 11: 6a price-history acquisition, 9a macro context, 9b macro and geopolitical events, 9c aggregate investor flows; current-decision baseline first; 3F records the accepted delay of the effective-N clock | 40B, 3F |
| 109 | Data acquisition and network policy: terms first, free/official first, paid only on owner approval, no scraping, one network module with allow-list and no redirects, secrets never in chat/repo/logs/URLs/errors, every response kept, versioned acquisition contracts | new 4G |
| 110 | Return forecasts: per horizon P(gain), P(outperform), absolute and excess return ranges (10/25/50/75/90th percentiles after costs), BUY/HOLD/SELL/ABSTAIN, invalidation condition; pinball loss and CRPS; interval coverage (10-90 range must hold the outcome ~80% of the time); a failing range is withheld; preregistered human-owned decision rule with owner-set thresholds | new 7A, 16, 18, 21, 36, 37 |
| 111 | Purpose and use: research for the owner's own decisions, never distributed as advice | 3 |
| 112 | 40C / "Current implementation position (v2.1.1)" describe the predecessor codebase | 40C, end |
| 113 | Acceptance criteria 90-104 and guardrails 17-20 | 47, 47A |

Control audit: 4,152 -> 4,453 lines; 303 inserted, 0 deleted. `tests/test_architecture_baseline.py`
re-runs the audit, checks criteria are exactly 1..104, and checks README.md and
docs/HANDOFF.md name the v2.2.0 document. Build/audit/PDF scripts: `data\handover\tools`
(build_v220.py, audit_v220.py, md2html.py).

What the owner was told and must keep being told honestly: the design produces
BUY/HOLD/SELL/ABSTAIN with calibrated probabilities and return ranges per horizon and
improves only when live calibration improves; nothing predicts anything until years of
price history exist (we have 6 weeks); profit is not guaranteed and "found no edge,
abstained" counts as success (49A); the assistant is not a licensed adviser.

## 13. Data-source research already done (do not repeat)

### 13.1 Exchange, brokers, vendors (2026-10-02)
- NSE Terms of Use forbid automated collection. robots.txt allows crawling but the terms
  bind the user.
- Free official route for history: SEBI circular of 20-Dec-2024 - exchanges share data
  for research via a request form to nseri@nse.co.in (BSE has its own form). Limit
  CROSS-VERIFIED 03/04-Oct-2026: 2 GB per researcher per YEAR (not per day), free;
  non-commercial.
- NSE paid: EOD Corporate Announcement product Rs 5,00,000/yr (SFTP); real-time
  corporate data Rs 10,60,000/yr.
- Broker APIs: Zerodha Kite Connect is "purely an execution platform"; Groww API
  (Rs 499/month) history only from 2020; Fyers and Upstox advertise free history; Dhan
  Rs 499/month. (Broker data terms usually forbid storage/redistribution - check first.)
- Authorised Indian vendors: TrueData, Global Datafeeds, Accord Fintech (ACE Equity).
  Trendlyne Rs 299/month AI-tool plan has too few calls.
- Global: Twelve Data Pro (~$229/month; NSE/BSE, US, Tokyo, Shanghai/Shenzhen, forex,
  fundamentals; personal use); FMP Ultimate (~$99/month annual); EODHD does NOT list
  Indian or Tokyo exchanges. Official free: SEC EDGAR, J-Quants (JPX), filings.xbrl.org,
  ECB, FRED.

### 13.2 News and regulators (2026-10-02/03)
- Business Standard: no automated collection, no caching, no AI/ML use incl. RAG. HT
  Digital (HT, Mint): no AI/ML use without written licence, RSS included. Economic Times:
  blocked. Moneycontrol: treated as not allowed.
- GDELT: open data, any use with citation; DOC API last 3 months, 250 articles per call;
  GDELT bulk files and Google BigQuery hold older history.
- Paid news APIs (terms on storage and AI use NOT yet checked): Marketaux, NewsData.io,
  NewsAPI.org (business $449/month).
- PIB: material may be reproduced free with prominent acknowledgement, not misleadingly.
- RBI: terms forbid caching and linking without written permission - NOT used (ADR-006).

### 13.3 Alpha Vantage (2026-10-03)
- Free key for individual non-commercial use; 25 requests/day; premium $49.99-249.99/month.
- NEWS_SENTIMENT fields and labels: see av_terms.txt; one call per company; tagging loose.
- Probe NOT run yet: `data\handover\tools\av_probe.py` (5 requests 20 s apart; key from
  ALPHAVANTAGE_API_KEY, never printed; answers to `data\handover\tools\av_samples\`). Owner:
  `$env:ALPHAVANTAGE_API_KEY = Read-Host "Alpha Vantage key"` then
  `python data\handover\tools\av_probe.py`, reply "probed".

### 13.4 Macro sources
- FRED/ALFRED: built in Stage 10C (section 10). Personal non-commercial use of third-party
  copyrighted series allowed except where the owner forbids (S&P Dow Jones Indices).
- MoSPI eSankhyiki: built in Stage 10C-2 (section 11). It also serves WPI (not MoSPI's -
  DPIIT terms unknown, not used) and CPI base 2012 (with provisional/final marks - not
  built yet).
- FBIL (USD/INR reference rate, G-sec/T-bill benchmarks, MIBOR): terms to check.
- FPI/FII flows (Stage 10E): NSDL publishes daily FPI investment (since Dec-1999 per the
  BAC-Brindco/nsdl-fpi catalogue; fortnightly sector data since 2011), CDSL, SEBI FPI
  pages; NSE provisional FII/DII cash-market figures (hand download only - NSE terms).
  NSDL terms to check FIRST.
- Not yet researched: GIFT Nifty (NSE IX), MSCI announcements, IMD monsoon data (imdlib,
  check IMD terms), China sources, sovereign ratings (licensed; use news).

### 13.5 GitHub / Hugging Face survey (03-Oct-2026) and the licensed-only decision
Full survey (names AND contents, many queries): `data\handover\research\github_survey_2026-10-03.md`.
Findings: many repos mirror NSE bhavcopies/index histories copied from NSE (not
authorised - NSE terms). Usable under their licences: exchange holiday calendars
(exchange_calendars, Apache-2.0 - used in 10C-2), IIMA Fama-French factors for India
(check terms), MoSPI's official code as reference only. Method references:
HaloHunter480/Survivorship-Bias-in-Emerging-Market-Small-Cap-Indices (survivor-only
backtests overstate Nifty Smallcap 250 returns by 4.94 pp a year), BAC-Brindco/nsdl-fpi
(NSDL catalogue, for 10E). To check later: captn3m0/india-isin-data (CC0, nightly NSDL
ISIN snapshots since 2021 - NSDL terms decide), iamsaswata/imdlib (IMD rainfall),
time-series-of-india/tsoi (RBI/NPCI payments - RBI terms), gtfintechlab/WorldCentralBanks.
The owner asked whether mirrors could be validated against our own files and used; the
decision (03-Oct-2026): LICENSED ONLY - mirrors not used even after checks; price history
via the NSE research request first, then an authorised paid vendor (owner approval with
price and terms).

### 13.6 NSE research-data request (drafted 03/04-Oct-2026; owner to send)
- `data\handover\nse_request\1_form_answers.txt`: answers for each field of NSE's form
  (owner downloaded the official form), objective (reproducible point-in-time record of
  NSE equities incl. delisted securities and corporate actions; measure survivorship and
  look-ahead bias; non-commercial; no redistribution), data sought ticks (U+2713): Daily
  reports, Monthly reports, Others (CM segment: daily bhavcopy, security-wise deliverable
  positions, securities available for trading, corporate actions, NIFTY 50 / NIFTY 500 /
  India VIX history, FII/DII cash-market activity); tick-by-tick left blank; justification.
- `data\handover\nse_request\2_email_to_nseri.txt`: covering email to nseri@nse.co.in.
- Risk: eligibility mentions accredited academic institutions; the owner applies as an
  independent researcher. If refused or too slow: authorised vendor quote (TrueData /
  Global Datafeeds / Accord), with the owner's approval.

### 13.7 FRED and MoSPI research artefacts
`data\handover\research\fred_samples\` (owner's probe of 03-Oct: 44 requests),
`mospi_samples\` (owner-approved samples 03/04-Oct), `mospi_live_2026-10-04\` (15 live
pages used for the smoke test), `calendars\` (CSV of closed weekdays, weekend sessions,
non-standard closes per calendar).

## 14. Roadmap (40B order) and the next step in detail

Done: steps 1-9 and 9a (Stage 7 = step 6; Stage 8/8B/8D = step 7; Stage 9 = step 8;
Stages 10/10B = step 9; 10C/10C-2 = step 9a; 8C = intake tooling). Next: 10D = step 9b,
10E = 9c, Stage 11 = step 10 (sentiment), Stage 7E = step 6a (price history, alongside,
waiting on NSE or a vendor). Then step 11 Knowledge/Event Hub, 12 Real Feature Factory,
13 Real Target Engine, 14 Equity Research Agent v0.1, 15 Prediction Ledger, 16 Shadow
operation, 17 Outcome Resolver, 18 Error Attribution, 19 Calibration + Abstention,
20 Decay/Drift, 21 Controlled Self-Learning, 22 Specialist agents, 23 API + Orchestrator.

NEXT: Stage 10D = 40B step 9b, Macro and Geopolitical Events.
- Read first in the architecture: 4A.0 (new event groups: monetary policy and rates;
  fiscal, trade and regulation; sovereign and macro data; geopolitics and shocks;
  index-provider and flow events), 4A rule 5 (an event without an issuer reaches a
  security only by declared read-across, sector membership or measured sensitivity,
  recorded), 3G, 4B, 4D, 4F.2, 4G, 5B, 5C, 40B step 9b and its acceptance text, 47/47A.
- Candidate sources (terms first; ask the owner before any new host - it would need an
  ADR-010 and allow-list change): GDELT (already allowed - DOC API themes/queries for
  conflict, oil, sanctions, central banks; GDELT Events/GKG bulk files would be new
  hosts), PIB press releases (reproduction allowed with acknowledgement - check its
  RSS/feeds and robots), SEBI feed (already in), MoSPI release calendar (scheduled
  releases as events, not proof of publication time), US/ECB/BoJ central-bank calendars
  (official sites - terms to check). RBI stays out (ADR-006).
- Design notes: event registry with group/type from 4A.0, no issuer -> read-across rules
  declared and recorded; availability from proven first-seen/retrieval; extraction
  confidence separate from investment confidence; never read article bodies from
  commercial sites.
- Then 10E (FPI/FII and DII daily flows - NSDL terms first), then Stage 11 sentiment
  (Alpha Vantage after the probe; exclude TradingView; 4B rules).
- Also owed: CPI food inflation with a narrower filter; CPI base 2012; WPI if DPIIT
  terms allow; India VIX/Nifty after NSE replies; calendars before 2026-12-31.

## 15. NSE real-data findings (the code depends on these)

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
- files carry Symbol and ISIN; family in the in-capmkt-ent namespace
  (IntegratedFinance_IndAS / Banking / NBFC / LI); taxonomy date varies;
- bank and insurer consolidated reports carry zeros or copies for regulatory ratios -
  taken from standalone only;
- March files say both Audited (year) and Unaudited (quarter);
- a revision row: TYPE OF SUBMISSION "Revision", BROADCAST blank, REVISED DATE/TIME like
  "24-JUL-2026 16:48:18", REVISION REMARKS text, dissemination = when the revised file
  went public.
- General insurers and other families are refused until checked on real files.
Announcements (CF-AN-equities-*.csv): columns SYMBOL, COMPANY NAME, SUBJECT, DETAILS,
BROADCAST DATE/TIME, RECEIPT, DISSEMINATION, DIFFERENCE, ATTACHMENT (no ISIN, no size);
attachment link = corporate/UPLOADER_ddmmyyyyhhmmss_originalname; one document filed
several times under different subjects within minutes; generic file names reused.
Registry names: legal names include ordinary words ('Take Solutions', 'Eternal',
'Nile'); 16 have no Limited/Ltd; NSE symbols that are ordinary words include BSE, OIL,
ONGC, PSB, INFY, TCS, IDEA.

## 16. Open items, deferred work and things NOT claimed

- Rows refused by an earlier code version cannot be re-read from a stored listing.
- Per-share figures not adjusted for bonuses/splits; balance sheet, cash flow, segments,
  half-year/nine-month periods not stored. NBFC GS3/AUM and insurer VNB/APE not in XBRL.
- Announcements: duplicates by file name and timing; direction/materiality/horizon not
  assessed; 125 rows (52 symbols) refused - companies not in EQUITY_L.
- News (Stage 10): headlines only; event type, direction, materiality, horizon not
  assessed; short forms not matched; only 6 companies have news names; no history older
  than GDELT's 3 months; first live fetch not run.
- SEBI (Stage 10B): titles only; releases before the first read missing; no RBI.
- Macro (10C/10C-2): see the not_claimed lists in stages/STAGE_10C_acceptance.yaml and
  STAGE_10C2_acceptance.yaml (section 11).
- Whole system: no sector classification yet (needed by 3G rule 4 and 9B); no 30-company
  cohort; price history only 6 trading days; universe versions empty; steps 11-23 not
  started; nothing is predicted yet.

## 17. Files kept for the next chat (`data\handover\`, git-ignored, on disk)

- `HANDOFF_new.md` - this file (copied to docs/HANDOFF.md in the 10C-2 commit).
- `stage10c2\files\` (10 tested new files), `stage10c2\patch_stage10c2.py` (already run
  by the owner - a second run STOPs), `stage10c2\patch_stage10c2_record.py` (to run,
  section 0.1).
- `stage10c\` - Stage 10C files, patch_stage10c.py and patch_stage10c_record.py (all done).
- `install_v220.py`, `arch220_files\` - v2.2.0 install (done).
- `nse_request\` - 1_form_answers.txt, 2_email_to_nseri.txt (section 13.6).
- `tools\` - build_v220.py, audit_v220.py, md2html.py, pdf_text.py, escape_tests.py;
  mutate_stage10.py, mutate_stage10b.py, mutate_stage10c.py, mutate_stage10c2.py
  (usage: `<venv python> mutate_stageX.py <scratch repo root>`); smoke_news.py,
  smoke_sebi.py, smoke_macro.py, smoke_10c2.py (real-data checks on a database copy:
  `<venv python> smoke_X.py <scratch repo root>`); analyse_gdelt.py, analyse_sebi.py;
  fetch_gdelt_samples.py (reference only); av_probe.py; fred_probe.py; mospi_probe.py
  (research probes, owner-approved); make_calendars.py, make_calendar_yaml.py,
  check_calendars.py (calendar generation and checks - need the xcal venv).
- `research\` - gdelt_samples, sebi_samples, fred_samples, mospi_samples,
  mospi_live_2026-10-04, calendars, av_terms.txt, github_survey_2026-10-03.md.
- Outside the repo: `C:\Users\nalin\AppData\Local\Temp\xcal` (exchange_calendars venv,
  143 MB; delete after the 10C-2 commit unless the owner wants it kept).

## 18. How to start the new chat

Paste this to the new chat:

> I am continuing my AI equity research agent project at
> C:\Users\nalin\Projects\ai-equity-agent. Please read docs/HANDOFF.md fully first (if
> data\handover\HANDOFF_new.md is newer, read that one), then the frozen architecture
> docs/Master_Architecture_v2_2_0_FROZEN.md sections named there. Verify the current state
> (git log, tests 740, database version 18, CI). If the Stage 10C-2 commit is not made
> yet, take me through section 0.1 of the handoff and verify; then continue with Stage 10D
> (architecture 40B step 9b, Macro and Geopolitical Events) using the same step-by-step
> method: research real data first, build and test in a scratch copy, give me paste
> blocks and commands, and verify after I reply "done". Tell me in advance whenever you
> need an API key and from which source - free options first.
