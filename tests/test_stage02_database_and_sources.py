"""Stage 2 acceptance tests.

40A item 5: the schema migrates from empty and rolls back cleanly.
40B step 2: every source declares authority, schema, frequency, timestamp
semantics and reliability - otherwise it is refused.
"""
import pytest

from core.database import connect, current_version, migrate, rollback
from ingestion.source_registry import (
    SourceRegistryError,
    get_source,
    list_sources,
    load_sources_file,
    register_source,
    sync_sources,
)


@pytest.fixture
def conn():
    c = connect(":memory:")
    migrate(c)
    yield c
    c.close()


def good_source(**changes):
    source = {
        "source_id": "test_source",
        "provider": "Test",
        "data_type": "prices",
        "endpoint": "https://example.com",
        "authority": "primary",
        "license": "test",
        "update_frequency": "daily",
        "historical_coverage": "2010-",
        "latency": "same day",
        "revision_policy": "none",
        "timestamp_semantics": "publication_time",
        "reliability_rating": "A",
        "authentication_method": "none",
        "schema_description": "one row per day",
    }
    source.update(changes)
    return source


def table_names(c):
    rows = c.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {r[0] for r in rows}


# ---- 40A item 5: migrate from empty, roll back cleanly ----

def test_schema_migrates_from_empty_and_rolls_back_cleanly():
    c = connect(":memory:")
    assert current_version(c) == 0
    assert migrate(c) >= 1
    assert "source_registry" in table_names(c)
    assert rollback(c, 0) == 0
    assert "source_registry" not in table_names(c)
    assert migrate(c) >= 1  # and can migrate again after rollback
    c.close()


def test_migrate_twice_is_harmless(conn):
    version = current_version(conn)
    assert migrate(conn) == version


# ---- 40B step 2: source registry ----

def test_complete_source_is_registered(conn):
    register_source(conn, good_source())
    assert get_source(conn, "test_source")["provider"] == "Test"


@pytest.mark.parametrize(
    "field",
    ["authority", "schema_description", "update_frequency",
     "timestamp_semantics", "reliability_rating"],
)
def test_source_missing_a_required_field_is_refused(conn, field):
    with pytest.raises(SourceRegistryError):
        register_source(conn, good_source(**{field: ""}))
    assert list_sources(conn) == []


def test_invalid_reliability_rating_is_refused(conn):
    with pytest.raises(SourceRegistryError):
        register_source(conn, good_source(reliability_rating="excellent"))


def test_invalid_timestamp_semantics_is_refused(conn):
    with pytest.raises(SourceRegistryError):
        register_source(conn, good_source(timestamp_semantics="whenever"))


def test_unknown_field_is_refused(conn):
    with pytest.raises(SourceRegistryError):
        register_source(conn, good_source(colour="blue"))


def test_duplicate_source_is_never_silently_overwritten(conn):
    register_source(conn, good_source())
    with pytest.raises(SourceRegistryError):
        register_source(conn, good_source(provider="Someone else"))
    assert get_source(conn, "test_source")["provider"] == "Test"


def test_unknown_source_raises(conn):
    with pytest.raises(SourceRegistryError):
        get_source(conn, "does_not_exist")


def test_project_sources_file_is_valid(conn):
    added = sync_sources(conn)
    assert len(added) == len(load_sources_file()) >= 3
    assert sync_sources(conn) == []  # second sync adds nothing
