"""Project commands. Usage:  python manage.py <command>

Commands:
  init-db   create or upgrade the database and register sources from config/sources.yaml
  sources   list registered sources
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from core.database import connect, migrate  # noqa: E402
from core.logging_setup import setup_logging  # noqa: E402
from ingestion.source_registry import list_sources, sync_sources  # noqa: E402


def init_db():
    log = setup_logging()
    conn = connect()
    version = migrate(conn)
    log.info("Database schema is at version %s", version)
    added = sync_sources(conn)
    log.info("Sources newly registered: %s", added or "none")
    conn.close()


def show_sources():
    conn = connect()
    migrate(conn)
    for source_id in list_sources(conn):
        print(source_id)
    conn.close()


COMMANDS = {"init-db": init_db, "sources": show_sources}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
