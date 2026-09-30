"""Stage 3 acceptance tests.

Section 4 entity resolution: ISIN is the key; the resolver returns exactly
one entity or raises; ambiguity raises; renames are events, not overwrites.
Section 6D: ISIN changes are events; old and new ISIN are never equivalent.
Section 4C: a null is never written without a missing-data class.
Sections 2A / 40 / 40D.1: acceptance records use the status vocabulary and
list what is NOT claimed.
"""
import pytest

from core.status import AcceptanceError, is_valid_status, load_acceptance_records, validate_acceptance
from core.database import MigrationError, connect, load_migrations, migrate, rollback
from data_quality.missing_data import (
    MissingClass,
    MissingDataError,
    check_imputable,
    check_reclassification,
    check_value,
)
from universe.entities import (
    AmbiguousIdentityError,
    EntityError,
    InvalidIsinError,
    UnknownEntityError,
    add_alias,
    add_entity,
    change_symbol,
    record_isin_change,
    resolve,
    validate_isin,
)

RELIANCE = "INE002A01018"
TCS = "INE467B01029"


@pytest.fixture
def conn():
    c = connect(":memory:")
    migrate(c)
    yield c
    c.close()


# ---- migrations folder ----

def test_all_migrations_roll_back_to_empty(conn):
    assert rollback(conn, 0) == 0
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    assert [t[0] for t in tables] == ["schema_version"]


def test_badly_named_migration_file_is_refused(tmp_path):
    (tmp_path / "entities.sql").write_text("SELECT 1;")
    with pytest.raises(MigrationError):
        load_migrations(tmp_path)


def test_migration_without_down_file_is_refused(tmp_path):
    (tmp_path / "0001_thing.up.sql").write_text("SELECT 1;")
    with pytest.raises(MigrationError):
        load_migrations(tmp_path)


# ---- ISIN validation ----

@pytest.mark.parametrize("isin", [RELIANCE, TCS, "INE009A01021", "US0378331005"])
def test_real_isins_are_valid(isin):
    assert validate_isin(isin) == isin


@pytest.mark.parametrize("bad", ["INE002A01019", "RELIANCE", "ine002a01018", "", None, "INE002A0101"])
def test_bad_isins_are_refused(bad):
    with pytest.raises(InvalidIsinError):
        validate_isin(bad)


# ---- entity resolution ----

def test_resolves_by_isin_and_by_symbol(conn):
    add_entity(conn, RELIANCE, "Reliance Industries Limited")
    add_alias(conn, RELIANCE, "nse_symbol", "RELIANCE", "1995-11-29")
    assert resolve(conn, RELIANCE, "2024-01-01") == RELIANCE
    assert resolve(conn, "RELIANCE", "2024-01-01") == RELIANCE


def test_unknown_identifier_raises(conn):
    with pytest.raises(UnknownEntityError):
        resolve(conn, "NOSUCHCO", "2024-01-01")


def test_no_fuzzy_matching(conn):
    add_entity(conn, RELIANCE, "Reliance Industries Limited")
    add_alias(conn, RELIANCE, "company_name", "Reliance Industries Limited", "1995-11-29")
    with pytest.raises(UnknownEntityError):
        resolve(conn, "Reliance Industries Ltd", "2024-01-01")


def test_symbol_not_valid_before_listing(conn):
    add_entity(conn, RELIANCE, "Reliance Industries Limited")
    add_alias(conn, RELIANCE, "nse_symbol", "RELIANCE", "1995-11-29")
    with pytest.raises(UnknownEntityError):
        resolve(conn, "RELIANCE", "1990-01-01")


def test_symbol_change_keeps_history(conn):
    add_entity(conn, TCS, "Example Ltd")
    add_alias(conn, TCS, "nse_symbol", "OLDNAME", "2010-01-01")
    change_symbol(conn, TCS, "OLDNAME", "NEWNAME", "2025-04-09")
    # Before the change only the old symbol works; after it only the new one.
    assert resolve(conn, "OLDNAME", "2025-04-08") == TCS
    assert resolve(conn, "NEWNAME", "2025-04-09") == TCS
    with pytest.raises(UnknownEntityError):
        resolve(conn, "OLDNAME", "2025-04-09")
    with pytest.raises(UnknownEntityError):
        resolve(conn, "NEWNAME", "2025-04-08")
    events = conn.execute("SELECT event_type FROM entity_events WHERE isin = ?", [TCS]).fetchall()
    assert events == [("symbol_change",)]


def test_failed_symbol_change_writes_nothing(conn):
    add_entity(conn, TCS, "Example Ltd")
    with pytest.raises(EntityError):
        change_symbol(conn, TCS, "NOTMINE", "NEWNAME", "2025-04-09")
    assert conn.execute("SELECT COUNT(*) FROM entity_aliases").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM entity_events").fetchone()[0] == 0


def test_reused_symbol_resolves_by_date(conn):
    add_entity(conn, RELIANCE, "Company A")
    add_entity(conn, TCS, "Company B")
    add_alias(conn, RELIANCE, "nse_symbol", "ABC", "2000-01-01", "2020-01-01")
    add_alias(conn, TCS, "nse_symbol", "ABC", "2021-01-01")
    assert resolve(conn, "ABC", "2019-06-01") == RELIANCE
    assert resolve(conn, "ABC", "2022-06-01") == TCS
    with pytest.raises(UnknownEntityError):
        resolve(conn, "ABC", "2020-06-01")  # nobody used it that year


def test_ambiguous_identifier_raises_never_guesses(conn):
    add_entity(conn, RELIANCE, "Company A")
    add_entity(conn, TCS, "Company B")
    add_alias(conn, RELIANCE, "vendor_id", "X1", "2000-01-01")
    add_alias(conn, TCS, "vendor_id", "X1", "2000-01-01")
    with pytest.raises(AmbiguousIdentityError):
        resolve(conn, "X1", "2024-01-01")


def test_entity_is_never_overwritten(conn):
    add_entity(conn, RELIANCE, "Reliance Industries Limited")
    with pytest.raises(EntityError):
        add_entity(conn, RELIANCE, "Something Else")


def test_bad_dates_are_refused(conn):
    add_entity(conn, RELIANCE, "Reliance Industries Limited")
    with pytest.raises(EntityError):
        add_alias(conn, RELIANCE, "nse_symbol", "RELIANCE", "29/11/1995")
    with pytest.raises(EntityError):
        add_alias(conn, RELIANCE, "nse_symbol", "RELIANCE", "2020-01-01", "2019-01-01")


# ---- Section 6D: ISIN is not permanently stable ----

INFOSYS = "INE009A01021"


def test_isin_change_is_an_event_not_an_equivalence(conn):
    add_entity(conn, RELIANCE, "Example Ltd (old ISIN)")
    add_entity(conn, INFOSYS, "Example Ltd (new ISIN)")
    record_isin_change(conn, RELIANCE, INFOSYS, "2024-06-01", "exchange circular ref 123")
    # Each ISIN still resolves only to itself - no global ISIN equivalence.
    assert resolve(conn, RELIANCE, "2025-01-01") == RELIANCE
    assert resolve(conn, INFOSYS, "2025-01-01") == INFOSYS
    row = conn.execute(
        "SELECT isin, related_isin, effective_date FROM entity_events WHERE event_type = 'isin_change'"
    ).fetchone()
    assert row == (RELIANCE, INFOSYS, "2024-06-01")


def test_isin_change_needs_evidence_and_two_known_isins(conn):
    add_entity(conn, RELIANCE, "Example Ltd")
    with pytest.raises(EntityError):
        record_isin_change(conn, RELIANCE, INFOSYS, "2024-06-01", "circular")  # new ISIN unknown
    add_entity(conn, INFOSYS, "Example Ltd new")
    with pytest.raises(EntityError):
        record_isin_change(conn, RELIANCE, INFOSYS, "2024-06-01", "")  # no evidence
    with pytest.raises(EntityError):
        record_isin_change(conn, RELIANCE, RELIANCE, "2024-06-01", "circular")
    assert conn.execute("SELECT COUNT(*) FROM entity_events").fetchone()[0] == 0


# ---- Sections 2A / 40 / 40D.1: status vocabulary and acceptance records ----

@pytest.mark.parametrize("status", ["CLOSED", "HELD", "AVAILABILITY_REVIEW", "ACCEPTED_IDENTITY_BASELINE"])
def test_valid_statuses(status):
    assert is_valid_status(status)


@pytest.mark.parametrize("status", ["REVIEW", "DONE", "ACCEPTED", "accepted_identity_baseline"])
def test_invalid_statuses(status):
    assert not is_valid_status(status)


def test_every_stage_has_a_valid_acceptance_record():
    records = load_acceptance_records()
    assert len(records) >= 4


def test_not_claimed_entries_must_be_exactly_false():
    record = {
        "stage": "x", "status": "CLOSED", "architecture": [], "proven": ["something"],
        "not_claimed": {"historical replay": True}, "negative_assertions": {"x happened": False},
    }
    with pytest.raises(AcceptanceError):
        validate_acceptance(record)


def test_acceptance_without_not_claimed_list_is_refused():
    record = {
        "stage": "x", "status": "CLOSED", "architecture": [], "proven": ["something"],
        "not_claimed": {}, "negative_assertions": {"x happened": False},
    }
    with pytest.raises(AcceptanceError):
        validate_acceptance(record)


# ---- Section 4C missing data ----

def test_null_without_class_is_rejected():
    with pytest.raises(MissingDataError):
        check_value(None)


def test_null_with_class_is_accepted():
    assert check_value(None, "not_disclosed") == (None, MissingClass.NOT_DISCLOSED)


def test_unknown_missing_class_is_rejected():
    with pytest.raises(ValueError):
        check_value(None, "just_missing")


def test_present_value_cannot_also_be_missing():
    with pytest.raises(MissingDataError):
        check_value(42.0, "not_disclosed")


def test_extraction_failure_never_silently_becomes_not_disclosed():
    with pytest.raises(MissingDataError):
        check_reclassification("extraction_failure", "not_disclosed")
    assert check_reclassification(
        "extraction_failure", "not_disclosed", evidence="checked filing page 14 by hand"
    ) == MissingClass.NOT_DISCLOSED


@pytest.mark.parametrize("cls", ["not_disclosed", "source_conflict", "extraction_failure"])
def test_these_classes_are_never_imputed(cls):
    with pytest.raises(MissingDataError):
        check_imputable(cls)


def test_exactly_six_missing_classes():
    assert len(MissingClass) == 6


def test_missing_migrations_folder_fails_loudly(tmp_path):
    with pytest.raises(MigrationError, match="not found"):
        load_migrations(tmp_path / "migrations")


def test_empty_migrations_folder_fails_loudly(tmp_path):
    with pytest.raises(MigrationError, match="No migration files"):
        load_migrations(tmp_path)
