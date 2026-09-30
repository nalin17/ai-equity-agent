"""Source Registry (architecture Section 4, 4F.2 and 40B step 2).

Every data source must be declared before any data from it is used. A source
that does not declare all required fields is refused. Nothing is guessed and
nothing is silently overwritten. Some source classes are excluded outright.
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
    "source_class",
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
    "source_class": {
        "exchange_official",   # NSE / BSE publications
        "regulator_official",  # SEBI, RBI
        "index_provider",      # NSE Indices
        "company_filing",      # documents filed by the company itself
        "licensed_vendor",     # paid data vendor under licence
        "news_publisher",      # attributable news outlet
        "public_social",       # public posts (restricted domain, 4B)
    },
    # primary = the original publisher (e.g. the exchange itself)
    "authority": {"primary", "secondary", "vendor"},
    # snapshot_no_vintage = only today's value is available; such fields are
    # withheld from historical runs (architecture 5A.1)
    "timestamp_semantics": {"publication_time", "effective_date", "snapshot_no_vintage"},
    # A = most reliable, D = least
    "reliability_rating": {"A", "B", "C", "D"},
}

# Architecture 4F.2: excluded, not down-weighted. These can never be registered.
EXCLUDED_SOURCE_CLASSES = {
    "private_tip_channel",          # messaging-group forwards, tip services
    "unattributed_rumour",          # "sources say" material with no named source
    "non_public_information",       # anything claiming pre-announcement inside information
}


class SourceRegistryError(Exception):
    """A source declaration is incomplete, invalid, excluded, duplicated or unknown."""


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
    if source["source_class"] in EXCLUDED_SOURCE_CLASSES:
        raise SourceRegistryError(
            f"Source '{source['source_id']}': source_class '{source['source_class']}' "
            "is an excluded source class (architecture 4F.2) and can never be registered"
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
    """Register every source in the file that is not registered yet.

    A source that is already registered must still match the file exactly.
    If they disagree, stop: the registry and the file never silently drift.
    """
    all_sources = load_sources_file(path)
    for source in all_sources:
        validate_source(source)  # check the whole file before writing anything
    registered = set(list_sources(conn))
    for source in all_sources:
        if source["source_id"] in registered:
            stored = get_source(conn, source["source_id"])
            changed = [f for f in REQUIRED_FIELDS if str(stored[f]) != str(source[f])]
            if changed:
                raise SourceRegistryError(
                    f"Source '{source['source_id']}' in the file differs from the registry "
                    f"in {changed}. Registrations are never silently changed."
                )
    added = []
    for source in all_sources:
        if source["source_id"] not in registered:
            register_source(conn, source)
            added.append(source["source_id"])
    return added
