"""Historical universe and survivorship (architecture 6A.1, 3A, 40B step 5).

A universe assembled from today's listed companies is survivor-biased by
construction: it overstates returns, understates drawdowns and makes
calibration look better than it is. So a universe here is never a query
against currently listed names. It is a VERSIONED HISTORY of membership:

  - who was a member, from which date, until which date, and why they left
    (delisted, merged, suspended, removed from the index, left the liquidity band)
  - an exit for delisting, merger or suspension must match a dated entity
    event (Stage 3) - first-class corporate actions, not free text
  - a version is frozen once created; a changed history is a new version
  - every replay run records the universe version it used
  - a replay over a period in which the universe cannot show any delisted or
    merged member is REJECTED, not warned about (6A.1 rule 4)

Two universes (3A): RESEARCH (broad, for statistics) and COVERAGE (the
cohort the research agent writes about). Coverage membership must lie inside
research membership. The coverage selection rule is written down with the
date of the data it used, and a replay may not start before that date -
otherwise the cohort was chosen using the period being evaluated (3A.2 rule 5).

Dates are "YYYY-MM-DD". A member on a date: member_from <= date < member_to.
"""
from datetime import datetime, timezone

from core.database import now_utc, run_in_transaction
from core.dates import strict_iso_date

KINDS = {"research", "coverage"}

# Exit reason -> the Stage 3 entity event that must exist on the exit date (or None).
EXIT_REASONS = {
    "delisted": "delisting",
    "merged": "merger",
    "suspended": "suspension",
    "removed_from_index": None,
    "left_liquidity_band": None,
}
LEFT_THE_MARKET = {"delisted", "merged"}


class UniverseError(Exception):
    """A universe, version, membership or replay breaks the 6A.1 / 3A rules."""


def _date(value, name):
    try:
        strict_iso_date(value)
    except ValueError:
        raise UniverseError(f"{name} must be YYYY-MM-DD, got {value!r}") from None
    return value


def _universe(conn, universe_id):
    row = conn.execute(
        "SELECT kind, parent_universe_id FROM universes WHERE universe_id = ?", [universe_id]
    ).fetchone()
    if row is None:
        raise UniverseError(f"Unknown universe {universe_id!r}")
    return row


def _version(conn, version_id):
    row = conn.execute(
        "SELECT v.universe_id, u.kind, v.rule_as_of, v.covers_from, v.covers_to"
        " FROM universe_versions v JOIN universes u ON u.universe_id = v.universe_id"
        " WHERE v.version_id = ?",
        [version_id],
    ).fetchone()
    if row is None:
        raise UniverseError(f"Unknown universe version {version_id}")
    return dict(zip(("universe_id", "kind", "rule_as_of", "covers_from", "covers_to"), row))


def create_universe(conn, universe_id, kind, description, parent_universe_id=None):
    if kind not in KINDS:
        raise UniverseError(f"kind must be one of {sorted(KINDS)}")
    if not description or not description.strip():
        raise UniverseError("A universe needs a description")
    if kind == "coverage":
        if parent_universe_id is None or _universe(conn, parent_universe_id)[0] != "research":
            raise UniverseError("A coverage universe must name its research universe (3A.2 rule 2)")
    elif parent_universe_id is not None:
        raise UniverseError("A research universe has no parent")
    if conn.execute("SELECT 1 FROM universes WHERE universe_id = ?", [universe_id]).fetchone():
        raise UniverseError(f"Universe {universe_id!r} already exists")
    conn.execute("INSERT INTO universes VALUES (?, ?, ?, ?, ?)",
                 [universe_id, kind, parent_universe_id, description.strip(), now_utc()])


def _check_member(conn, m, covers_from, covers_to):
    isin = m.get("isin")
    if not conn.execute("SELECT 1 FROM entities WHERE isin = ?", [isin]).fetchone():
        raise UniverseError(f"No entity with ISIN {isin}")
    start = _date(m.get("member_from"), "member_from")
    end, reason = m.get("member_to"), m.get("exit_reason")
    if (end is None) != (reason is None):
        raise UniverseError(f"{isin}: an exit date needs an exit reason, and an exit reason needs a date")
    if end is not None:
        _date(end, "member_to")
        if end <= start:
            raise UniverseError(f"{isin}: member_to must be after member_from")
        if end > covers_to:
            raise UniverseError(f"{isin}: exit {end} is after the period this version covers")
        if reason not in EXIT_REASONS:
            raise UniverseError(f"{isin}: exit_reason must be one of {sorted(EXIT_REASONS)}")
        event = EXIT_REASONS[reason]
        if event and not conn.execute(
            "SELECT 1 FROM entity_events WHERE isin = ? AND event_type = ? AND effective_date = ?",
            [isin, event, end],
        ).fetchone():
            raise UniverseError(
                f"{isin}: exit '{reason}' on {end} has no matching '{event}' entity event on that date"
            )
    if start > covers_to or (end is not None and end <= covers_from):
        raise UniverseError(f"{isin}: membership does not overlap the covered period")
    return isin, start, end, reason


def _contained_in_parent(conn, parent_version_id, isin, start, end):
    rows = conn.execute(
        "SELECT member_from, member_to FROM universe_membership WHERE version_id = ? AND isin = ?",
        [parent_version_id, isin],
    ).fetchall()
    for p_start, p_end in rows:
        if p_start <= start and (p_end is None or (end is not None and end <= p_end)):
            return True
    return False


def create_universe_version(conn, universe_id, selection_rule, rule_as_of, covers_from, covers_to,
                            members, parent_version_id=None):
    """Freeze a new version of a universe's membership history. Returns version_id."""
    kind, _ = _universe(conn, universe_id)
    if not selection_rule or not selection_rule.strip():
        raise UniverseError("The selection rule must be written down before use (3A.2 rule 5)")
    _date(rule_as_of, "rule_as_of")
    _date(covers_from, "covers_from")
    _date(covers_to, "covers_to")
    if covers_to <= covers_from:
        raise UniverseError("covers_to must be after covers_from")
    if rule_as_of > datetime.now(timezone.utc).date().isoformat():
        raise UniverseError("rule_as_of is in the future: a rule cannot use data that does not exist yet")
    if not members:
        raise UniverseError("A universe version needs members")

    checked = [_check_member(conn, m, covers_from, covers_to) for m in members]

    by_isin = {}
    for isin, start, end, _ in checked:
        by_isin.setdefault(isin, []).append((start, end))
    for isin, spans in by_isin.items():
        spans.sort()
        for (s1, e1), (s2, _) in zip(spans, spans[1:]):
            if e1 is None or e1 > s2:
                raise UniverseError(f"{isin}: overlapping membership periods")

    if kind == "coverage":
        if parent_version_id is None:
            raise UniverseError("A coverage version must name the research version it sits inside")
        parent = _version(conn, parent_version_id)
        if parent["universe_id"] != _universe(conn, universe_id)[1]:
            raise UniverseError("parent_version_id belongs to a different research universe")
        for isin, start, end, _ in checked:
            if not _contained_in_parent(conn, parent_version_id, isin, start, end):
                raise UniverseError(f"{isin}: covered but not eligible in the research universe (3A.2 rule 2)")
    elif parent_version_id is not None:
        raise UniverseError("A research version has no parent version")

    def work(c):
        version = c.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM universe_versions WHERE universe_id = ?", [universe_id]
        ).fetchone()[0]
        version_id = c.execute(
            "INSERT INTO universe_versions (universe_id, version, selection_rule, rule_as_of, covers_from,"
            " covers_to, parent_version_id, member_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [universe_id, version, selection_rule.strip(), rule_as_of, covers_from, covers_to,
             parent_version_id, len(checked), now_utc()],
        ).lastrowid
        c.executemany(
            "INSERT INTO universe_membership VALUES (?, ?, ?, ?, ?)",
            [(version_id, isin, start, end, reason) for isin, start, end, reason in checked],
        )
        return version_id

    return run_in_transaction(conn, work)


def _check_window(v, start, end):
    _date(start, "start")
    _date(end, "end")
    if end < start:
        raise UniverseError("end must not be before start")
    if start < v["covers_from"] or end > v["covers_to"]:
        raise UniverseError(
            f"This universe version covers {v['covers_from']} to {v['covers_to']} only; "
            "it makes no claim about other dates"
        )


def members_on(conn, version_id, on_date):
    """ISINs that were members on one date, as recorded in this version."""
    v = _version(conn, version_id)
    _check_window(v, on_date, on_date)
    rows = conn.execute(
        "SELECT DISTINCT isin FROM universe_membership WHERE version_id = ?"
        " AND member_from <= ? AND (member_to IS NULL OR ? < member_to) ORDER BY isin",
        [version_id, on_date, on_date],
    ).fetchall()
    return [r[0] for r in rows]


def members_during(conn, version_id, start, end):
    """ISINs that were members at ANY point in [start, end] - including those that later left."""
    v = _version(conn, version_id)
    _check_window(v, start, end)
    rows = conn.execute(
        "SELECT DISTINCT isin FROM universe_membership WHERE version_id = ?"
        " AND member_from <= ? AND (member_to IS NULL OR member_to > ?) ORDER BY isin",
        [version_id, end, start],
    ).fetchall()
    return [r[0] for r in rows]


def start_replay(conn, version_id, period_start, period_end, purpose):
    """Open a replay run over a period. Refused unless the universe is survivorship-aware for it."""
    v = _version(conn, version_id)
    _check_window(v, period_start, period_end)
    if not purpose or not purpose.strip():
        raise UniverseError("A replay run must state its purpose")
    if v["kind"] == "coverage" and period_start < v["rule_as_of"]:
        raise UniverseError(
            f"The coverage cohort was selected with data as of {v['rule_as_of']}; replaying from "
            f"{period_start} would evaluate it on the period used to choose it (3A.2 rule 5)"
        )
    placeholders = ", ".join("?" * len(LEFT_THE_MARKET))
    exits = conn.execute(
        f"SELECT COUNT(*) FROM universe_membership WHERE version_id = ? AND exit_reason IN ({placeholders})"
        " AND member_to > ? AND member_to <= ?",
        [version_id, *sorted(LEFT_THE_MARKET), period_start, period_end],
    ).fetchone()[0]
    if exits == 0:
        raise UniverseError(
            f"Universe version {version_id} shows no delisted or merged member between {period_start} and "
            f"{period_end}. It cannot demonstrate survivorship for this period, so the replay is "
            "rejected (6A.1 rule 4)."
        )
    replay_id = conn.execute(
        "INSERT INTO replay_runs (universe_version_id, period_start, period_end, purpose, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        [version_id, period_start, period_end, purpose.strip(), now_utc()],
    ).lastrowid
    return {
        "replay_id": replay_id,
        "universe_version_id": version_id,
        "members": members_during(conn, version_id, period_start, period_end),
    }
