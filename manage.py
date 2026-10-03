"""Project commands. Usage:  python manage.py <command> [files...]

Commands:
  init-db                   create or upgrade the database and register sources
  sources                   list registered sources
  load-equity-list FILE     load NSE's list of listed securities (EQUITY_L.csv)
  ingest-prices FILE [...]  run NSE bhavcopy files (.csv or .zip) through the trust chain
  load-corporate-actions FILE   load NSE's corporate actions file (CF-CA-equities-*.csv)
  compare-series SYMBOL START END  raw vs corporate-action-adjusted closes (dates YYYY-MM-DD)
  bridge-isins              bridge ISIN changes at recorded splits/bonuses (6D), then retry quarantined rows
  load-results-index FILE [...]  load NSE results listings (CF-FR-*.csv or CF-Integrated-Filing-*.csv) -
                            load these before the XBRL files
  load-results FILE [...]   load NSE results XBRL files (INDAS_*.xml or INTEGRATED_FILING_*.xml)
  show-fundamentals SYMBOL [PERIOD_END]  list the stored results figures for one company (date YYYY-MM-DD)
  load-announcements FILE [...]  load NSE corporate announcements (CF-AN-equities-*.csv)
  show-events SYMBOL [FROM] [TO]  list one company's events - one per release (dates YYYY-MM-DD)
  fetch-news [--symbols A,B] [--from YYYY-MM-DD]  fetch news from GDELT for the companies in
                            config/news_names.yaml - the only command that uses the internet
  show-news SYMBOL [FROM] [TO]  list one company's news stories - copies of one story shown once
  ingest-inbox [--without-listing] [FOLDER]  move NSE downloads from FOLDER (default: your Downloads)
                            into data/inbox, then load every new file in the right order
  checklist [LISTING ...] [--symbols A,B] [--since YYYY-MM-DD] [--prices-from YYYY-MM-DD]
                            write data/checklist.html - links to the files still to download
  report                    show what is in the database

Files are downloaded by hand from nseindia.com: NSE's terms of use prohibit
automated collection (ADR-004). The time a file is ingested is recorded as its
retrieval time: it is the moment the data verifiably entered this system
(architecture 5B.2).

News is the one exception: fetch-news asks GDELT, whose terms allow automated use,
and nothing else (ADR-005). Article links are never opened.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from core.config import PROJECT_ROOT, load_config  # noqa: E402
from core.database import connect, migrate, run_in_transaction  # noqa: E402
from core.dates import strict_iso_date  # noqa: E402
from core.logging_setup import setup_logging  # noqa: E402
from features.price_series import AdjustmentBlocked, adjusted_series, raw_series  # noqa: E402
from ingestion.intake import checklist_items, collect_downloads, ingest_inbox, write_checklist  # noqa: E402
from ingestion.gdelt_news import ENTITY_RULE, extract, stories, sync_news_names  # noqa: E402
from ingestion.gdelt_news import DEDUP_RULE as NEWS_DEDUP_RULE  # noqa: E402
from ingestion.market_adapters import ingest_market_file, retry_quarantined  # noqa: E402
from ingestion.news_fetch import MIN_INTERVAL, Fetcher, default_window, fetch_company  # noqa: E402
from ingestion.nse_announcements import DEDUP_RULE, MAPPING_VERSION, events, load_announcements  # noqa: E402
from ingestion.nse_corporate_actions import load_corporate_actions  # noqa: E402
from ingestion.nse_financial_results import load_results_index, load_results_xbrl  # noqa: E402
from ingestion.nse_financial_results import IST  # noqa: E402
from ingestion.source_registry import list_sources, sync_sources  # noqa: E402
from provenance.availability import parse_timestamp  # noqa: E402
from universe.entities import resolve  # noqa: E402
from universe.equity_list import load_equity_list  # noqa: E402
from universe.identity_bridges import BridgeRefused, bridge_candidates, create_bridge  # noqa: E402


def open_db():
    conn = connect()
    migrate(conn)
    return conn


def init_db(args):
    log = setup_logging()
    conn = connect()
    version = migrate(conn)
    log.info("Database schema is at version %s", version)
    added = sync_sources(conn)
    log.info("Sources newly registered: %s", added or "none")
    conn.close()


def show_sources(args):
    conn = open_db()
    for source_id in list_sources(conn):
        print(source_id)
    conn.close()


def load_list(args):
    if len(args) != 1:
        raise SystemExit("Usage: python manage.py load-equity-list FILE")
    log = setup_logging()
    conn = open_db()
    report = load_equity_list(conn, args[0], datetime.now(timezone.utc))
    log.info("Equity list: %s", report)
    conn.close()


def ingest_prices(args):
    if not args:
        raise SystemExit("Usage: python manage.py ingest-prices FILE [FILE ...]")
    log = setup_logging()
    conn = open_db()
    failed = 0
    for name in args:
        try:
            report = ingest_market_file(conn, name, datetime.now(timezone.utc))
            log.info("%s: %s", Path(name).name, report)
        except Exception as e:  # report and carry on with the next file; nothing partial is stored
            failed += 1
            log.error("%s: NOT INGESTED - %s: %s", Path(name).name, type(e).__name__, e)
    conn.close()
    if failed:
        raise SystemExit(f"{failed} file(s) were not ingested - see the messages above")


def load_ca(args):
    if len(args) != 1:
        raise SystemExit("Usage: python manage.py load-corporate-actions FILE")
    log = setup_logging()
    conn = open_db()
    result = load_corporate_actions(conn, args[0], datetime.now(timezone.utc))
    log.info("Corporate actions: %s", result)
    conn.close()


def compare_series(args):
    if len(args) != 3:
        raise SystemExit("Usage: python manage.py compare-series SYMBOL START END")
    symbol, start, end = args
    conn = open_db()
    isin = resolve(conn, symbol, end, alias_type="nse_symbol")
    raw = raw_series(conn, isin, start, end, follow_bridges=True)
    try:
        adjusted = adjusted_series(conn, isin, start, end)
    except AdjustmentBlocked as e:
        adjusted = None
        print(f"Adjusted series BLOCKED: {e}")
    actions = conn.execute(
        "SELECT ex_date, action_type, treatment, shares_before, shares_after, terms_text FROM corporate_actions"
        " WHERE isin = ? AND ex_date > ? AND ex_date <= ? ORDER BY ex_date", [isin, start, end]).fetchall()
    print(f"{symbol} ({isin}) from {start} to {end}")
    for ex_date, kind, treatment, before, after, terms in actions:
        ratio = f" {before}->{after} shares" if before else ""
        print(f"  action on {ex_date}: {kind} [{treatment}]{ratio}  ({terms})")
    for bridge_id, old_isin, ex_date in conn.execute(
            "SELECT bridge_id, old_isin, ex_date FROM identity_bridges WHERE new_isin = ? AND ex_date > ?"
            " AND ex_date <= ?", [isin, start, end]):
        print(f"  identity bridge {bridge_id}: before {ex_date} this security traded as {old_isin}")
    print(f"  {'date':<12}{'isin':<14}{'raw close':>12}{'raw move':>10}{'adjusted':>12}{'adj move':>10}")
    previous = None
    for i, row in enumerate(raw.rows):
        adj = adjusted.rows[i][4] if adjusted else None
        raw_move = f"{row[4] / previous[0] - 1:+.1%}" if previous else ""
        adj_move = f"{adj / previous[1] - 1:+.1%}" if previous and adj is not None else ""
        adj_text = f"{adj:.2f}" if adj is not None else "-"
        print(f"  {row[0]:<12}{raw.row_isins[i]:<14}{row[4]:>12.2f}{raw_move:>10}{adj_text:>12}{adj_move:>10}")
        previous = (row[4], adj)
    conn.close()


def bridge_isins(args):
    log = setup_logging()
    conn = open_db()
    created, refused = [], {}
    for symbol, ex_date in bridge_candidates(conn):
        try:
            created.append(create_bridge(conn, symbol, ex_date))
        except BridgeRefused as e:
            refused[f"{symbol} {ex_date}"] = str(e)
    for b in created:
        log.info("Bridge %s: %s %s -> %s at the %s on %s", b["bridge_id"], b["symbol"], b["old_isin"],
                 b["new_isin"], b["action"], b["ex_date"])
    log.info("Bridges created: %s | no bridge (evidence incomplete): %s", len(created), len(refused))
    for key, reason in refused.items():
        print(f"   no bridge  {key}: {reason}")
    if created:
        old_isins = {b["old_isin"] for b in created}
        artifacts = [r[0] for r in conn.execute(
            "SELECT DISTINCT r.artifact_id FROM quarantine q JOIN ingestion_runs r ON r.run_id = q.run_id"
            " JOIN adapter_runs a ON a.run_id = r.run_id ORDER BY 1")]
        for artifact_id in artifacts:
            result = retry_quarantined(conn, artifact_id, "identity bridges recorded (6D)", only_isins=old_isins)
            if result["rows_retried"]:
                log.info("Retry of artifact %s: %s", artifact_id,
                         {k: result.get(k) for k in ("rows_retried", "rows_trusted", "rows_quarantined")})
    conn.close()


def load_results_listing(args):
    if not args:
        raise SystemExit("Usage: python manage.py load-results-index FILE [FILE ...]")
    log = setup_logging()
    conn = open_db()
    failed = 0
    for name in args:
        try:
            log.info("%s: %s", Path(name).name, load_results_index(conn, name, datetime.now(timezone.utc)))
        except Exception as e:  # report and carry on with the next file; nothing partial is stored
            failed += 1
            log.error("%s: NOT LOADED - %s: %s", Path(name).name, type(e).__name__, e)
    conn.close()
    if failed:
        raise SystemExit(f"{failed} file(s) were not loaded - see the messages above")


def load_results(args):
    if not args:
        raise SystemExit("Usage: python manage.py load-results FILE [FILE ...]")
    log = setup_logging()
    conn = open_db()
    failed = 0
    for name in args:
        try:
            result = load_results_xbrl(conn, name, datetime.now(timezone.utc))
            log.info("%s: %s", Path(name).name, {k: v for k, v in result.items() if k != "problems"})
            for problem in result["problems"]:
                print(f"     {problem}")
        except Exception as e:  # report and carry on with the next file; nothing partial is stored
            failed += 1
            log.error("%s: NOT LOADED - %s: %s", Path(name).name, type(e).__name__, e)
    conn.close()
    if failed:
        raise SystemExit(f"{failed} file(s) were not loaded - see the messages above")


def show_fundamentals(args):
    if len(args) not in (1, 2):
        raise SystemExit("Usage: python manage.py show-fundamentals SYMBOL [PERIOD_END]")
    conn = open_db()
    isins = [r[0] for r in conn.execute(
        "SELECT DISTINCT isin FROM entity_aliases WHERE alias_type = 'nse_symbol' AND alias_value = ?", [args[0]])]
    if not isins:
        raise SystemExit(f"Unknown symbol {args[0]}")
    marks = ", ".join("?" * len(isins))
    period = " AND f.period_end = ?" if len(args) == 2 else ""
    rows = conn.execute(
        "SELECT f.period_end, f.basis, f.field, f.value, f.missing_class, f.unit, f.version, a.published_at"
        f" FROM pit_facts f JOIN raw_artifacts a ON a.artifact_id = f.artifact_id WHERE f.isin IN ({marks}){period}"
        " ORDER BY f.period_end, f.basis, f.field, f.version", isins + args[1:]).fetchall()
    print(f"{' '.join(args)}: {len(rows)} figures (INR amounts shown in crore, ratios in percent)")
    print(f"  {'period end':<12}{'basis':<14}{'field':<44}{'value':>14}  published")
    for end, basis, field, value, missing, unit, version, published in rows:
        if value is None:
            shown = f"[{missing}]"
        elif unit == "INR":
            shown = f"{value / 1e7:,.2f}"
        elif unit == "ratio":
            shown = f"{value:.2%}"
        else:
            shown = f"{value:,.2f}"
        when = published[:16] if published else "not proven"
        print(f"  {end:<12}{basis:<14}{field + (f' v{version}' if version > 1 else ''):<44}{shown:>14}  {when}")
    conn.close()


def load_announcement_files(args):
    if not args:
        raise SystemExit("Usage: python manage.py load-announcements FILE [FILE ...]")
    log = setup_logging()
    conn = open_db()
    failed = 0
    for name in args:
        try:
            result = load_announcements(conn, name, datetime.now(timezone.utc))
            log.info("%s: %s", Path(name).name, {k: v for k, v in result.items() if k != "problems"})
            for problem in result["problems"]:
                print(f"     {problem}")
        except Exception as e:  # report and carry on with the next file; nothing partial is stored
            failed += 1
            log.error("%s: NOT LOADED - %s: %s", Path(name).name, type(e).__name__, e)
    conn.close()
    if failed:
        raise SystemExit(f"{failed} file(s) were not loaded - see the messages above")


def show_events(args):
    if not 1 <= len(args) <= 3:
        raise SystemExit("Usage: python manage.py show-events SYMBOL [FROM] [TO]")
    start = strict_iso_date(args[1]).isoformat() if len(args) > 1 else "0001-01-01"
    end = strict_iso_date(args[2]).isoformat() if len(args) > 2 else "9999-12-31"
    conn = open_db()
    isins = [r[0] for r in conn.execute(
        "SELECT DISTINCT isin FROM entity_aliases WHERE alias_type = 'nse_symbol' AND alias_value = ?", [args[0]])]
    if not isins:
        raise SystemExit(f"Unknown symbol {args[0]}")
    now = datetime.now(timezone.utc)
    found = [e for isin in isins for e in events(conn, now, isin=isin) if start <= e["published_at"][:10] <= end]
    print(f"{args[0]}: {len(found)} events (rule {DEDUP_RULE}, types {MAPPING_VERSION}); times are first dissemination")
    for e in found:
        print(f"  {e['published_at'][:16]}  {e['kind']:<15} {', '.join(e['event_types']) or '-':<26} filings: {len(e['filings'])}")
        for subject, when in e["subjects"].items():
            print(f"         {when[:16]}  {subject}")
    conn.close()


def fetch_news(args):
    usage = "Usage: python manage.py fetch-news [--symbols A,B] [--from YYYY-MM-DD]"
    options, i = {}, 0
    while i < len(args):
        if args[i] in ("--symbols", "--from") and i + 1 < len(args):
            options[args[i]] = args[i + 1]
            i += 2
        else:
            raise SystemExit(usage)
    log = setup_logging()
    conn = open_db()
    added = sync_news_names(conn)
    if added:
        log.info("News names newly recorded: %s", ", ".join(added))
    companies = conn.execute(
        "SELECT DISTINCT n.isin, s.alias_value FROM entity_aliases n JOIN entity_aliases s ON s.isin = n.isin"
        " AND s.alias_type = 'nse_symbol' AND s.valid_to IS NULL WHERE n.alias_type = 'news_name'"
        " ORDER BY s.alias_value").fetchall()
    if "--symbols" in options:
        wanted = options["--symbols"].split(",")
        unknown = sorted(set(wanted) - {symbol for _, symbol in companies})
        if unknown:
            raise SystemExit(f"No news names for {', '.join(unknown)} - add them to config/news_names.yaml")
        companies = [(isin, symbol) for isin, symbol in companies if symbol in wanted]
    start = None
    if "--from" in options:
        day = strict_iso_date(options["--from"])
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    fetcher = Fetcher(on_wait=lambda seconds, why: log.info("Waiting %.0f seconds: %s", seconds, why))
    log.info("Fetching news from GDELT for %s companies - at least %.0f seconds between requests",
             len(companies), MIN_INTERVAL)
    failed = 0
    for isin, symbol in companies:
        begin, end = default_window(conn, isin, datetime.now(timezone.utc))
        try:
            for result in fetch_company(conn, fetcher, isin, symbol, start or begin, end, fetched_dir()):
                problems = result.pop("problems", [])
                log.info("%s %s: %s", symbol, result.pop("window"), result)
                for problem in problems:
                    print(f"     {problem}")
        except Exception as e:  # report and carry on with the next company; nothing partial is stored
            failed += 1
            log.error("%s: NOT FETCHED - %s: %s", symbol, type(e).__name__, e)
    log.info("GDELT requests: %s (refused and retried: %s). News data: The GDELT Project, gdeltproject.org",
             fetcher.requests, fetcher.refusals)
    conn.close()
    if failed:
        raise SystemExit(f"{failed} compan{'y was' if failed == 1 else 'ies were'} not fetched - see the"
                         " messages above; run fetch-news again later")


def show_news(args):
    if not 1 <= len(args) <= 3:
        raise SystemExit("Usage: python manage.py show-news SYMBOL [FROM] [TO]")
    start = strict_iso_date(args[1]).isoformat() if len(args) > 1 else "0001-01-01"
    end = strict_iso_date(args[2]).isoformat() if len(args) > 2 else "9999-12-31"
    conn = open_db()
    isins = [r[0] for r in conn.execute(
        "SELECT DISTINCT isin FROM entity_aliases WHERE alias_type = 'nse_symbol' AND alias_value = ?", [args[0]])]
    if not isins:
        raise SystemExit(f"Unknown symbol {args[0]}")
    run_in_transaction(conn, extract)
    found = []
    for isin in isins:
        for story in stories(conn, datetime.now(timezone.utc), isin=isin):
            when = parse_timestamp(story["published_at"]).astimezone(IST)
            if start <= when.date().isoformat() <= end:
                found.append((when, story, story["companies"].get(isin)))
    sys.stdout.reconfigure(errors="replace")
    roles = [held["role"] if held else "search only" for _, _, held in found]
    print(f"{args[0]}: {len(found)} stories - about it: {roles.count('subject')}, mentioning it:"
          f" {roles.count('mentioned')}, only returned by its search (not listed): {roles.count('search only')}")
    print(f"  rules {ENTITY_RULE} and {NEWS_DEDUP_RULE}; times are India time, when each story was proven"
          " public. News data: The GDELT Project, gdeltproject.org")
    for when, story, held in found:
        if held is None:
            continue
        how = f"{held['role']} ({held['extraction_confidence']})"
        copies = len(story["copies"])
        print(f"  {when:%Y-%m-%d %H:%M}  {how:<47} {story['copies'][0]['domain']}"
              + (f" +{copies - 1} cop{'y' if copies == 2 else 'ies'}" if copies > 1 else ""))
        print(f"                    {story['headline'][:110]}")
    conn.close()


def fetched_dir():
    return PROJECT_ROOT / load_config()["paths"]["data_dir"] / "fetched"


def inbox_dir():
    return PROJECT_ROOT / load_config()["paths"]["data_dir"] / "inbox"


def ingest_inbox_files(args):
    flags = [a for a in args if a.startswith("--")]
    folders = [a for a in args if not a.startswith("--")]
    if set(flags) - {"--without-listing"} or len(folders) > 1:
        raise SystemExit("Usage: python manage.py ingest-inbox [--without-listing] [DOWNLOADS_FOLDER]")
    downloads = Path(folders[0]) if folders else Path.home() / "Downloads"
    log = setup_logging()
    conn = open_db()
    if downloads.is_dir():
        moved = collect_downloads(downloads, inbox_dir())
        log.info("From %s: %s file(s) moved into the inbox", downloads, len(moved["moved"]))
        for name in moved["already_in_inbox"]:
            print(f"     already in the inbox (left where it is): {name}")
        for name in moved["name_clash"]:
            print(f"     NOT MOVED - a different file with this name is already in the inbox: {name}")
    else:
        log.warning("No folder %s - nothing collected", downloads)
    counts = {}
    for name, kind, outcome, detail in ingest_inbox(conn, inbox_dir(),
                                                    require_listing="--without-listing" not in flags):
        counts[outcome] = counts.get(outcome, 0) + 1
        if outcome == "loaded":
            problems = detail.get("problems", []) if isinstance(detail, dict) else []
            log.info("%s: %s", name, {k: v for k, v in detail.items() if k != "problems"}
                     if isinstance(detail, dict) else detail)
            for problem in problems:
                print(f"     {problem}")
        elif outcome == "failed":
            log.error("%s: NOT LOADED - %s", name, detail)
        elif outcome == "waiting" or kind is None:
            log.warning("%s: %s", name, detail)
    log.info("Inbox: %s", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "empty")
    conn.close()
    if counts.get("failed"):
        raise SystemExit(f"{counts['failed']} file(s) were not loaded - see the messages above")


def make_checklist(args):
    usage = ("Usage: python manage.py checklist [LISTING_FILE ...] [--symbols A,B] [--since YYYY-MM-DD]"
             " [--prices-from YYYY-MM-DD]")
    options, files, i = {}, [], 0
    while i < len(args):
        if args[i] in ("--symbols", "--since", "--prices-from") and i + 1 < len(args):
            options[args[i]] = args[i + 1]
            i += 2
        elif args[i].startswith("--"):
            raise SystemExit(usage)
        else:
            files.append(args[i])
            i += 1
    if not files and "--prices-from" not in options:
        raise SystemExit(usage)
    conn = open_db()
    symbols = options["--symbols"].split(",") if "--symbols" in options else None
    items = checklist_items(conn, files, inbox_dir(), symbols, options.get("--since"), options.get("--prices-from"))
    out = inbox_dir().parent / "checklist.html"
    todo = write_checklist(items, out)
    print(f"{todo} file(s) to download, {len(items) - todo} already in the inbox or database.")
    print(f"Open the checklist with:  start {out}")
    conn.close()


def report(args):
    conn = open_db()
    one = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    print(f"Entities (companies):      {one('SELECT COUNT(*) FROM entities')}")
    print(f"Raw files stored:          {one('SELECT COUNT(*) FROM raw_artifacts')}")
    print(f"Price files ingested:      {one('SELECT COUNT(*) FROM ingestion_runs')}")
    print(f"Trusted daily prices:      {one('SELECT COUNT(*) FROM trusted_prices')}")
    first, last = conn.execute("SELECT MIN(trade_date), MAX(trade_date) FROM trusted_prices").fetchone()
    print(f"Trading dates covered:     {first} to {last}")
    print(f"Corporate actions:         {one('SELECT COUNT(*) FROM corporate_actions')}")
    for treatment, n in conn.execute(
            "SELECT treatment, COUNT(*) FROM corporate_actions GROUP BY 1 ORDER BY 2 DESC"):
        print(f"   {treatment:<28} {n}")
    print(f"Quarantined price rows:    {one('SELECT COUNT(*) FROM quarantine')}  (all runs, kept as history)")
    print("   still unresolved (distinct rows): " + str(one(
        "SELECT COUNT(*) FROM (SELECT DISTINCT r.artifact_id, q.row_number FROM quarantine q"
        " JOIN ingestion_runs r ON r.run_id = q.run_id) x WHERE NOT EXISTS (SELECT 1 FROM price_provenance p"
        " JOIN ingestion_runs r2 ON r2.run_id = p.run_id WHERE r2.artifact_id = x.artifact_id"
        " AND p.row_number = x.row_number)")))
    print(f"Identity bridges (6D):     {one('SELECT COUNT(*) FROM identity_bridges')}")
    print(f"Results filings listed:    {one('SELECT COUNT(*) FROM fr_filings')} (old page)"
          f" + {one('SELECT COUNT(*) FROM if_filings')} (integrated filing)")
    print(f"Results files loaded:      {one('SELECT COUNT(*) FROM fr_loads')}"
          f"  (figures corrected by revisions: {one('SELECT COALESCE(SUM(facts_corrected), 0) FROM fr_loads')})")
    print(f"Announcements (filings):   {one('SELECT COUNT(*) FROM an_filings')}"
          f"  -> events: {len(events(conn, datetime.now(timezone.utc)))} (rule {DEDUP_RULE})")
    print(f"News articles (GDELT):     {one('SELECT COUNT(*) FROM nw_articles')}"
          f"  from {one('SELECT COUNT(*) FROM nw_responses')} responses")
    print(f"Fundamental figures:       {one('SELECT COUNT(*) FROM pit_facts')}"
          f"  (stored as missing: {one('SELECT COUNT(*) FROM pit_facts WHERE value IS NULL')})")
    for stage, n in conn.execute(
            "SELECT failed_stage, COUNT(*) FROM quarantine GROUP BY 1 ORDER BY 2 DESC"):
        print(f"   {stage:<28} {n}")
    print("Most common reasons among unresolved rows:")
    for reason, n in conn.execute(
            "SELECT substr(q.reason, 1, 90), COUNT(DISTINCT r.artifact_id || ':' || q.row_number) FROM quarantine q"
            " JOIN ingestion_runs r ON r.run_id = q.run_id WHERE NOT EXISTS (SELECT 1 FROM price_provenance p"
            " JOIN ingestion_runs r2 ON r2.run_id = p.run_id WHERE r2.artifact_id = r.artifact_id"
            " AND p.row_number = q.row_number) GROUP BY 1 ORDER BY 2 DESC LIMIT 5"):
        print(f"   {n:>6}  {reason}")
    conn.close()


COMMANDS = {
    "init-db": init_db,
    "sources": show_sources,
    "load-equity-list": load_list,
    "ingest-prices": ingest_prices,
    "load-corporate-actions": load_ca,
    "compare-series": compare_series,
    "bridge-isins": bridge_isins,
    "load-results-index": load_results_listing,
    "load-results": load_results,
    "show-fundamentals": show_fundamentals,
    "load-announcements": load_announcement_files,
    "show-events": show_events,
    "fetch-news": fetch_news,
    "show-news": show_news,
    "ingest-inbox": ingest_inbox_files,
    "checklist": make_checklist,
    "report": report,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
