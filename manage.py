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
  report                    show what is in the database

Files are downloaded by hand from nseindia.com into data/inbox. The time a
file is ingested is recorded as its retrieval time: it is the moment the data
verifiably entered this system (architecture 5B.2).
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from core.database import connect, migrate  # noqa: E402
from core.logging_setup import setup_logging  # noqa: E402
from features.price_series import AdjustmentBlocked, adjusted_series, raw_series  # noqa: E402
from ingestion.market_adapters import ingest_market_file, retry_quarantined  # noqa: E402
from ingestion.nse_corporate_actions import load_corporate_actions  # noqa: E402
from ingestion.nse_financial_results import load_results_index, load_results_xbrl  # noqa: E402
from ingestion.source_registry import list_sources, sync_sources  # noqa: E402
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
    print(f"Results files loaded:      {one('SELECT COUNT(*) FROM fr_loads')}")
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
    "report": report,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
