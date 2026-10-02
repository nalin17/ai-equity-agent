-- Historical universe and survivorship (architecture 6A.1, 3A, 40B step 5).
--
-- A universe is never "today's listed companies". It is a versioned history
-- of who was a member, from when, until when, and why they left. A version is
-- frozen once created; a changed history is a new version.

CREATE TABLE universes (
    universe_id        TEXT PRIMARY KEY,
    kind               TEXT NOT NULL CHECK (kind IN ('research', 'coverage')),
    parent_universe_id TEXT REFERENCES universes(universe_id),
    description        TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    -- 3A.2 rule 2: a coverage universe always sits inside a research universe.
    CHECK ((kind = 'coverage') = (parent_universe_id IS NOT NULL))
) STRICT;

CREATE TABLE universe_versions (
    version_id        INTEGER PRIMARY KEY,
    universe_id       TEXT NOT NULL REFERENCES universes(universe_id),
    version           INTEGER NOT NULL,
    selection_rule    TEXT NOT NULL,     -- 3A.2 rule 5: written down before use
    rule_as_of        TEXT NOT NULL,     -- the date of the data the rule used
    covers_from       TEXT NOT NULL,     -- the period this membership history claims to cover
    covers_to         TEXT NOT NULL,
    parent_version_id INTEGER REFERENCES universe_versions(version_id),
    member_count      INTEGER NOT NULL,  -- freezes the version: no rows can be added later
    created_at        TEXT NOT NULL,
    UNIQUE (universe_id, version),
    CHECK (covers_to > covers_from)
) STRICT;

CREATE TABLE universe_membership (
    version_id  INTEGER NOT NULL REFERENCES universe_versions(version_id),
    isin        TEXT NOT NULL REFERENCES entities(isin),
    member_from TEXT NOT NULL,
    member_to   TEXT,          -- empty means still a member at covers_to
    exit_reason TEXT,          -- required whenever member_to is set
    CHECK ((member_to IS NULL) = (exit_reason IS NULL)),
    CHECK (member_to IS NULL OR member_to > member_from)
) STRICT;

CREATE INDEX idx_universe_membership ON universe_membership (version_id, isin);

-- 6A.1 rule 3: every replay run records the universe version it used.
CREATE TABLE replay_runs (
    replay_id           INTEGER PRIMARY KEY,
    universe_version_id INTEGER NOT NULL REFERENCES universe_versions(version_id),
    period_start        TEXT NOT NULL,
    period_end          TEXT NOT NULL,
    purpose             TEXT NOT NULL,
    created_at          TEXT NOT NULL
) STRICT;

-- A version is frozen: once its declared members are in, nothing more can be added.
CREATE TRIGGER universe_membership_frozen BEFORE INSERT ON universe_membership
WHEN (SELECT COUNT(*) FROM universe_membership WHERE version_id = NEW.version_id)
     >= (SELECT member_count FROM universe_versions WHERE version_id = NEW.version_id)
BEGIN SELECT RAISE(ABORT, 'universe version is frozen: create a new version instead'); END;

-- History is append-only.
CREATE TRIGGER universes_no_update BEFORE UPDATE ON universes
BEGIN SELECT RAISE(ABORT, 'universes is append-only'); END;
CREATE TRIGGER universes_no_delete BEFORE DELETE ON universes
BEGIN SELECT RAISE(ABORT, 'universes is append-only'); END;
CREATE TRIGGER universe_versions_no_update BEFORE UPDATE ON universe_versions
BEGIN SELECT RAISE(ABORT, 'universe_versions is append-only'); END;
CREATE TRIGGER universe_versions_no_delete BEFORE DELETE ON universe_versions
BEGIN SELECT RAISE(ABORT, 'universe_versions is append-only'); END;
CREATE TRIGGER universe_membership_no_update BEFORE UPDATE ON universe_membership
BEGIN SELECT RAISE(ABORT, 'universe_membership is append-only'); END;
CREATE TRIGGER universe_membership_no_delete BEFORE DELETE ON universe_membership
BEGIN SELECT RAISE(ABORT, 'universe_membership is append-only'); END;
CREATE TRIGGER replay_runs_no_update BEFORE UPDATE ON replay_runs
BEGIN SELECT RAISE(ABORT, 'replay_runs is append-only'); END;
CREATE TRIGGER replay_runs_no_delete BEFORE DELETE ON replay_runs
BEGIN SELECT RAISE(ABORT, 'replay_runs is append-only'); END;
