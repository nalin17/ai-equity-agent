"""Project commands. Usage:  python manage.py <command> [files...]

Commands:
  init-db                   create or upgrade the database and register sources
  sources                   list registered sources
  load-equity-list FILE     load NSE's list of listed securities (EQUITY_L.csv)
  ingest-prices FILE [...]  run NSE bhavcopy files (.csv or .zip) through the trust chain
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
from ingestion.market_adapters import ingest_market_file  # noqa: E402
from ingestion.source_registry import list_sources, sync_sources  # noqa: E402
from universe.equity_list import load_equity_list  # noqa: E402


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


def report(args):
    conn = open_db()
    one = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    print(f"Entities (companies):      {one('SELECT COUNT(*) FROM entities')}")
    print(f"Raw files stored:          {one('SELECT COUNT(*) FROM raw_artifacts')}")
    print(f"Price files ingested:      {one('SELECT COUNT(*) FROM ingestion_runs')}")
    print(f"Trusted daily prices:      {one('SELECT COUNT(*) FROM trusted_prices')}")
    first, last = conn.execute("SELECT MIN(trade_date), MAX(trade_date) FROM trusted_prices").fetchone()
    print(f"Trading dates covered:     {first} to {last}")
    print(f"Quarantined price rows:    {one('SELECT COUNT(*) FROM quarantine')}")
    for stage, n in conn.execute(
            "SELECT failed_stage, COUNT(*) FROM quarantine GROUP BY 1 ORDER BY 2 DESC"):
        print(f"   {stage:<28} {n}")
    print("Most common quarantine reasons:")
    for reason, n in conn.execute(
            "SELECT substr(reason, 1, 90), COUNT(*) FROM quarantine GROUP BY 1 ORDER BY 2 DESC LIMIT 5"):
        print(f"   {n:>6}  {reason}")
    conn.close()


COMMANDS = {
    "init-db": init_db,
    "sources": show_sources,
    "load-equity-list": load_list,
    "ingest-prices": ingest_prices,
    "report": report,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
