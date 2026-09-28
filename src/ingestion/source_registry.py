"""Source Registry (architecture Section 4 and 40B step 2).

Every data source must be declared before any data from it is used. A source
that does not declare all required fields is refused. Nothing is guessed and
nothing is silently overwritten.
"""
from pathlib import Path

import yaml

from core.config import PROJECT_ROOT
from core.database import now_utc

SOURCES_FILE = PROJECT_ROOT / "config" / "sources.yaml"

REQUIRED_FIELDS = (
    "source_id",
    "provider",
    "data_type",
    "endpoint",
    "authority",
    "license",
    "update_frequency",
    "historical_coverage",
    "latency",
    "revision_policy",
    "timestamp_semantics",
    "reliability_rating",
    "authentication_method",
    "schema_description",
)

ALLOWED_VALUES = {
    # primary = the original publisher (e.g. the exchange itself)
    "authority": {"primary", "secondary", "vendor"},
    # snapshot_no_vintage = only today's value is available; such fields are
    # withheld from historical runs (architecture 5A.1)
    "timestamp_semantics": {"publication_time", "effective_date", "snapshot_no_vintage"},
    # A = most reliable, D = least
    "reliability_rating": {"A", "B", "C", "D"},
}


class SourceRegistryError(Exception):
    """A source declaration is incomplete, invalid, duplicated or unknown."""


def validate_source(source):
    missing = [f for f in REQUIRED_FIELDS if not str(source.get(f) or "").strip()]
    if missing:
        raise SourceRegistryError(
            f"Source '{source.get('source_id')}' is missing fields: {missing}"
        )
    unknown = sorted(set(source) - set(REQUIRED_FIELDS))
    if unknown:
        raise SourceRegistryError(
            f"Source '{source['source_id']}' has unknown fields: {unknown}"
        )
    for field, allowed in ALLOWED_VALUES.items():
        if source[field] not in allowed:
            raise SourceRegistryError(
                f"Source '{source['source_id']}': {field}='{source[field]}' "
                f"is not one of {sorted(allowed)}"
            )


def register_source(conn, source):
    validate_source(source)
    exists = conn.execute(
        "SELECT 1 FROM source_registry WHERE source_id = ?", [source["source_id"]]
    ).fetchone()
    if exists:
        raise SourceRegistryError(
            f"Source '{source['source_id']}' is already registered; "
            "registrations are never silently overwritten"
        )
    values = [source[f] for f in REQUIRED_FIELDS] + [now_utc()]
    placeholders = ", ".join("?" * len(values))
    columns = ", ".join(REQUIRED_FIELDS) + ", registered_at"
    conn.execute(f"INSERT INTO source_registry ({columns}) VALUES ({placeholders})", values)


def get_source(conn, source_id):
    cursor = conn.execute("SELECT * FROM source_registry WHERE source_id = ?", [source_id])
    row = cursor.fetchone()
    if row is None:
        raise SourceRegistryError(f"Unknown source: '{source_id}'")
    columns = [d[0] for d in cursor.description]
    return dict(zip(columns, row))


def list_sources(conn):
    rows = conn.execute("SELECT source_id FROM source_registry ORDER BY 1").fetchall()
    return [r[0] for r in rows]


def load_sources_file(path=SOURCES_FILE):
    with open(Path(path), encoding="utf-8-sig") as f:
        data = yaml.safe_load(f) or {}
    return data.get("sources", [])


def sync_sources(conn, path=SOURCES_FILE):
    """Register every source in the file that is not registered yet."""
    all_sources = load_sources_file(path)
    for source in all_sources:
        validate_source(source)  # check the whole file before writing anything
    registered = set(list_sources(conn))
    added = []
    for source in all_sources:
        if source["source_id"] not in registered:
            register_source(conn, source)
            added.append(source["source_id"])
    return added
