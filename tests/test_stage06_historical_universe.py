"""Stage 6 acceptance tests: historical universe and survivorship.

40B step 5 / 40A: replay over a period containing a delisting includes the
delisted name.
6A.1: membership is a versioned point-in-time table; exits are dated
corporate actions; every replay records its universe version; a replay that
cannot demonstrate delisted members for its period is rejected.
3A.2: coverage sits inside research; cohort selection is written down and
dated, and is never evaluated on the period used to choose it.
Also: the strict date fix found during this stage.
"""
import sqlite3

import pytest

from core.database import connect, migrate, rollback
from core.dates import strict_iso_date
from universe.entities import EntityError, add_alias, add_entity, record_event
from universe.historical_universe import (
    UniverseError,
    create_universe,
    create_universe_version,
    members_during,
    members_on,
    start_replay,
)

SURVIVOR_1 = "INE002A01018"
SURVIVOR_2 = "INE467B01029"
DELISTED = "INE062A01020"
MERGED = "INE001A01036"
LEFT_INDEX = "INE090A01021"

RULE = "All NSE EQ-series securities listed at any time in the covered period"
COVERS = ("2020-01-01", "2025-12-31")


@pytest.fixture
def conn():
    c = connect(":memory:")
    migrate(c)
    for isin, name in [(SURVIVOR_1, "Survivor One"), (SURVIVOR_2, "Survivor Two"),
                       (DELISTED, "Delisted Co"), (MERGED, "Merged Away Co"), (LEFT_INDEX, "Left Index Co")]:
        add_entity(c, isin, name)
    record_event(c, DELISTED, "delisting", "2023-06-30", "compulsory delisting")
    record_event(c, MERGED, "merger", "2023-07-01", "merged into Survivor One", related_isin=SURVIVOR_1)
    yield c
    c.close()


def history():
    return [
        {"isin": SURVIVOR_1, "member_from": "2020-01-01"},
        {"isin": SURVIVOR_2, "member_from": "2020-01-01"},
        {"isin": DELISTED, "member_from": "2020-01-01", "member_to": "2023-06-30", "exit_reason": "delisted"},
        {"isin": MERGED, "member_from": "2020-01-01", "member_to": "2023-07-01", "exit_reason": "merged"},
        {"isin": LEFT_INDEX, "member_from": "2021-03-01", "member_to": "2023-09-01",
         "exit_reason": "removed_from_index"},
    ]


@pytest.fixture
def research(conn):
    create_universe(conn, "nse_research", "research", "Broad NSE research universe")
    return create_universe_version(conn, "nse_research", RULE, COVERS[1], *COVERS, history())


# ---- 40B step 5: the acceptance test ----

def test_replay_over_a_period_with_a_delisting_includes_the_delisted_name(conn, research):
    run = start_replay(conn, research, "2023-01-01", "2023-12-31", "acceptance test")
    assert DELISTED in run["members"] and MERGED in run["members"]
    assert run["members"] == sorted([SURVIVOR_1, SURVIVOR_2, DELISTED, MERGED, LEFT_INDEX])
    # The replay records the universe version it used (6A.1 rule 3).
    stored = conn.execute("SELECT universe_version_id FROM replay_runs WHERE replay_id = ?",
                          [run["replay_id"]]).fetchone()
    assert stored == (research,)


def test_membership_is_point_in_time(conn, research):
    assert DELISTED in members_on(conn, research, "2023-06-29")      # last day listed
    assert DELISTED not in members_on(conn, research, "2023-06-30")  # gone from the exit date
    assert LEFT_INDEX not in members_on(conn, research, "2021-02-28")  # not yet a member
    # "Today's list" is exactly the survivor-biased view the architecture forbids
    # using for history: it has lost every company that left.
    assert members_on(conn, research, COVERS[1]) == sorted([SURVIVOR_1, SURVIVOR_2])


# ---- 6A.1 rule 4: replay without survivorship evidence is rejected ----

def test_replay_without_any_delisting_in_the_period_is_rejected(conn, research):
    with pytest.raises(UniverseError, match="cannot demonstrate survivorship"):
        start_replay(conn, research, "2024-01-01", "2024-12-31", "survivor-only period")
    assert conn.execute("SELECT COUNT(*) FROM replay_runs").fetchone()[0] == 0


def test_index_removal_alone_does_not_count_as_survivorship_evidence(conn, research):
    # 2023-08-01 to 2023-12-31 contains only the index removal (2023-09-01).
    with pytest.raises(UniverseError, match="cannot demonstrate survivorship"):
        start_replay(conn, research, "2023-08-01", "2023-12-31", "x")


def test_replay_outside_the_covered_period_is_rejected(conn, research):
    with pytest.raises(UniverseError, match="covers"):
        start_replay(conn, research, "2019-01-01", "2023-12-31", "x")
    with pytest.raises(UniverseError, match="covers"):
        members_on(conn, research, "2026-01-02")


def test_replay_must_state_its_purpose(conn, research):
    with pytest.raises(UniverseError, match="purpose"):
        start_replay(conn, research, "2023-01-01", "2023-12-31", "  ")


# ---- 6A.1 rule 2: exits are dated corporate actions ----

def test_delisting_exit_needs_a_matching_entity_event(conn):
    create_universe(conn, "u", "research", "test")
    bad = [{"isin": SURVIVOR_1, "member_from": "2020-01-01", "member_to": "2022-01-01",
            "exit_reason": "delisted"}]
    with pytest.raises(UniverseError, match="no matching 'delisting' entity event"):
        create_universe_version(conn, "u", RULE, "2025-12-31", *COVERS, bad)


@pytest.mark.parametrize("member", [
    {"isin": DELISTED, "member_from": "2020-01-01", "member_to": "2023-06-30"},           # date, no reason
    {"isin": DELISTED, "member_from": "2020-01-01", "exit_reason": "delisted"},           # reason, no date
    {"isin": DELISTED, "member_from": "2020-01-01", "member_to": "2023-06-30", "exit_reason": "vanished"},
    {"isin": DELISTED, "member_from": "2023-07-01", "member_to": "2023-06-30", "exit_reason": "delisted"},
    {"isin": "INE040A01034", "member_from": "2020-01-01"},                                 # unknown company
    {"isin": SURVIVOR_1, "member_from": "20200101"},                                       # compact date
])
def test_bad_memberships_are_refused(conn, member):
    create_universe(conn, "u", "research", "test")
    with pytest.raises(UniverseError):
        create_universe_version(conn, "u", RULE, "2025-12-31", *COVERS, [member])
    assert conn.execute("SELECT COUNT(*) FROM universe_versions").fetchone()[0] == 0


def test_overlapping_membership_is_refused_but_rejoining_is_allowed(conn):
    create_universe(conn, "u", "research", "test")
    overlapping = [
        {"isin": LEFT_INDEX, "member_from": "2020-01-01", "member_to": "2022-01-01", "exit_reason": "removed_from_index"},
        {"isin": LEFT_INDEX, "member_from": "2021-06-01"},
    ]
    with pytest.raises(UniverseError, match="overlapping"):
        create_universe_version(conn, "u", RULE, "2025-12-31", *COVERS, overlapping)
    rejoined = [
        {"isin": LEFT_INDEX, "member_from": "2020-01-01", "member_to": "2022-01-01", "exit_reason": "removed_from_index"},
        {"isin": LEFT_INDEX, "member_from": "2023-01-01"},
    ]
    v = create_universe_version(conn, "u", RULE, "2025-12-31", *COVERS, rejoined)
    assert members_on(conn, v, "2022-06-01") == []
    assert members_on(conn, v, "2023-06-01") == [LEFT_INDEX]


# ---- 6A.1 rule 1: versioned and frozen ----

def test_a_version_is_frozen(conn, research):
    with pytest.raises(sqlite3.DatabaseError, match="frozen"):
        conn.execute("INSERT INTO universe_membership VALUES (?, ?, '2020-01-01', NULL, NULL)",
                     [research, "INE040A01034"])
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE universe_membership SET member_to = NULL")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM universe_membership")


def test_a_corrected_history_is_a_new_version_and_the_old_one_is_unchanged(conn, research):
    corrected = [m for m in history() if m["isin"] != LEFT_INDEX]
    v2 = create_universe_version(conn, "nse_research", RULE + " (index removals excluded)", "2025-12-31",
                                 *COVERS, corrected)
    assert v2 != research
    assert LEFT_INDEX in members_on(conn, research, "2022-01-01")
    assert LEFT_INDEX not in members_on(conn, v2, "2022-01-01")
    versions = conn.execute("SELECT version FROM universe_versions ORDER BY version").fetchall()
    assert versions == [(1,), (2,)]


# ---- 3A: research and coverage universes ----

def test_coverage_must_sit_inside_research(conn, research):
    create_universe(conn, "cohort", "coverage", "Coverage cohort", parent_universe_id="nse_research")
    outside = [{"isin": LEFT_INDEX, "member_from": "2020-01-01"}]  # research has it only from 2021-03-01
    with pytest.raises(UniverseError, match="not eligible in the research universe"):
        create_universe_version(conn, "cohort", "Top names by liquidity on 2022-12-30", "2022-12-30",
                                *COVERS, outside, parent_version_id=research)
    inside = [{"isin": SURVIVOR_1, "member_from": "2023-01-02"}, {"isin": SURVIVOR_2, "member_from": "2023-01-02"}]
    v = create_universe_version(conn, "cohort", "Top names by liquidity on 2022-12-30", "2022-12-30",
                                *COVERS, inside, parent_version_id=research)
    assert members_on(conn, v, "2024-01-02") == sorted([SURVIVOR_1, SURVIVOR_2])


def test_coverage_is_never_evaluated_on_the_period_used_to_choose_it(conn, research):
    create_universe(conn, "cohort", "coverage", "Coverage cohort", parent_universe_id="nse_research")
    members = [{"isin": DELISTED, "member_from": "2020-01-01", "member_to": "2023-06-30",
                "exit_reason": "delisted"}, {"isin": SURVIVOR_1, "member_from": "2020-01-01"}]
    v = create_universe_version(conn, "cohort", "Liquidity rank on 2022-12-30", "2022-12-30",
                                *COVERS, members, parent_version_id=research)
    with pytest.raises(UniverseError, match="3A.2 rule 5"):
        start_replay(conn, v, "2022-01-01", "2023-12-31", "would look back into the selection period")
    assert start_replay(conn, v, "2023-01-01", "2023-12-31", "after selection")["replay_id"] > 0


def test_universe_kinds_are_enforced(conn):
    with pytest.raises(UniverseError):
        create_universe(conn, "c", "coverage", "no parent")
    create_universe(conn, "r", "research", "research")
    with pytest.raises(UniverseError):
        create_universe(conn, "r2", "research", "research with a parent", parent_universe_id="r")
    with pytest.raises(UniverseError):
        create_universe(conn, "x", "favourites", "not a kind")


@pytest.mark.parametrize("rule, rule_as_of", [("", "2025-12-31"), (RULE, "2999-01-01"), (RULE, "31-12-2025")])
def test_selection_rule_must_be_written_and_dated_honestly(conn, rule, rule_as_of):
    create_universe(conn, "u", "research", "test")
    with pytest.raises(UniverseError):
        create_universe_version(conn, "u", rule, rule_as_of, *COVERS, history())


# ---- the strict date fix (found in this stage) ----

@pytest.mark.parametrize("bad", ["20240101", "2024-W01-1", "2024-1-1", "2024-02-30", "", None])
def test_only_canonical_dates_are_accepted(bad):
    with pytest.raises(ValueError):
        strict_iso_date(bad)


def test_compact_dates_can_no_longer_reach_the_entity_tables(conn):
    with pytest.raises(EntityError):
        add_alias(conn, SURVIVOR_1, "nse_symbol", "ABC", "20200101")


# ---- migration and acceptance record ----

def test_universe_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 5)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not {"universes", "universe_versions", "universe_membership", "replay_runs"} & names
    assert "pit_facts" in names
    c.close()


def test_stage_6_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_06_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_HISTORICAL_UNIVERSE_BASELINE"
    assert record["not_claimed"]["real NSE listing and delisting history loaded"] is False
