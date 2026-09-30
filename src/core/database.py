"""Database connection and schema migrations.

Uses SQLite, which is built into Python (see docs/decisions/ADR-001).

Architecture 40A, item 5: the schema must migrate from empty and roll back
cleanly. Every change to the database structure is a pair of numbered files
in the migrations/ folder:

    0002_entities.up.sql     applies the change
    0002_entities.down.sql   undoes it

Never edit an old migration file; add a new numbered pair.
"""
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.config import PROJECT_ROOT, load_config

MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
MIGRATION_NAME = re.compile(r"^(\d{4})_(\w+)\.(up|down)\.sql$")


class MigrationError(Exception):
    """The migrations folder is inconsistent."""


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_migrations(folder=MIGRATIONS_DIR):
    """Return [(version, description, up_sql, down_sql)] sorted by version."""
    folder = Path(folder)
    if not folder.is_dir():
        raise MigrationError(f"Migrations folder not found: {folder}")
    found = {}
    for path in Path(folder).glob("*.sql"):
        match = MIGRATION_NAME.match(path.name)
        if not match:
            raise MigrationError(f"Badly named migration file: {path.name}")
        version, description, direction = int(match[1]), match[2], match[3]
        entry = found.setdefault(version, {"description": description})
        if entry["description"] != description:
            raise MigrationError(f"Migration {version} has two different names")
        entry[direction] = path.read_text(encoding="utf-8-sig")
    migrations = []
    for version in sorted(found):
        entry = found[version]
        if "up" not in entry or "down" not in entry:
            raise MigrationError(f"Migration {version} needs both .up.sql and .down.sql")
        migrations.append((version, entry["description"], entry["up"], entry["down"]))
    if not migrations:
        raise MigrationError(f"No migration files found in {folder}")
    if [m[0] for m in migrations] != list(range(1, len(migrations) + 1)):
        raise MigrationError("Migration numbers must be 1, 2, 3, ... with no gaps")
    return migrations


def connect(path=None):
    """Open the project database. Use ':memory:' for a throwaway database."""
    if path is None:
        path = PROJECT_ROOT / load_config()["paths"]["database"]
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), autocommit=True)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_version_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at  TEXT NOT NULL
        ) STRICT
        """
    )


def current_version(conn):
    _ensure_version_table(conn)
    return conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0]


def _apply(conn, script, bookkeeping_sql, params):
    """Run a migration script and its bookkeeping row as one transaction."""
    conn.execute("BEGIN")
    try:
        conn.executescript(script)
        conn.execute(bookkeeping_sql, params)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def migrate(conn):
    """Apply every migration not yet applied. Safe to run repeatedly."""
    start = current_version(conn)
    for version, description, up_sql, _ in load_migrations():
        if version > start:
            _apply(conn, up_sql, "INSERT INTO schema_version VALUES (?, ?, ?)",
                   (version, description, now_utc()))
    return current_version(conn)


def rollback(conn, target_version=0):
    """Undo migrations, newest first, down to target_version."""
    start = current_version(conn)
    for version, _, _, down_sql in reversed(load_migrations()):
        if target_version < version <= start:
            _apply(conn, down_sql, "DELETE FROM schema_version WHERE version = ?", (version,))
    return current_version(conn)


def run_in_transaction(conn, work):
    """Run work(conn) so that either all of its writes happen or none do."""
    conn.execute("BEGIN")
    try:
        result = work(conn)
        conn.execute("COMMIT")
        return result
    except Exception:
        conn.execute("ROLLBACK")
        raise
