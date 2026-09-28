"""Database connection and schema migrations.

Uses SQLite, which is built into Python (see docs/decisions/ADR-001).

Architecture 40A, item 5: the schema must migrate from empty and roll back
cleanly. Every change to the database structure is a numbered migration with
an "up" step (apply) and a "down" step (undo). Never edit an old migration;
add a new one.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.config import PROJECT_ROOT, load_config

# (version, description, up_sql, down_sql)
# STRICT tables make SQLite refuse values of the wrong type instead of
# silently storing them.
MIGRATIONS = [
    (
        1,
        "create source registry",
        """
        CREATE TABLE source_registry (
            source_id             TEXT PRIMARY KEY,
            provider              TEXT NOT NULL,
            data_type             TEXT NOT NULL,
            endpoint              TEXT NOT NULL,
            authority             TEXT NOT NULL,
            license               TEXT NOT NULL,
            update_frequency      TEXT NOT NULL,
            historical_coverage   TEXT NOT NULL,
            latency               TEXT NOT NULL,
            revision_policy       TEXT NOT NULL,
            timestamp_semantics   TEXT NOT NULL,
            reliability_rating    TEXT NOT NULL,
            authentication_method TEXT NOT NULL,
            schema_description    TEXT NOT NULL,
            registered_at         TEXT NOT NULL
        ) STRICT
        """,
        "DROP TABLE source_registry",
    ),
]


def now_utc():
    return datetime.now(timezone.utc).isoformat()


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


def _run_in_transaction(conn, *statements):
    conn.execute("BEGIN")
    try:
        for sql, params in statements:
            conn.execute(sql, params)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def migrate(conn):
    """Apply every migration not yet applied. Safe to run repeatedly."""
    start = current_version(conn)
    for version, description, up_sql, _ in MIGRATIONS:
        if version > start:
            _run_in_transaction(
                conn,
                (up_sql, ()),
                ("INSERT INTO schema_version VALUES (?, ?, ?)", (version, description, now_utc())),
            )
    return current_version(conn)


def rollback(conn, target_version=0):
    """Undo migrations, newest first, down to target_version."""
    start = current_version(conn)
    for version, _, _, down_sql in reversed(MIGRATIONS):
        if target_version < version <= start:
            _run_in_transaction(
                conn,
                (down_sql, ()),
                ("DELETE FROM schema_version WHERE version = ?", (version,)),
            )
    return current_version(conn)
