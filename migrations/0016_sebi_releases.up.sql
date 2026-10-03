-- SEBI's releases from its RSS feed (architecture 40B step 9, 4A, 4E, 5B; ADR-006).
-- The companies a release names and its kind are derived by versioned rules; they are not stored.

-- One row per read of the feed that was kept.
CREATE TABLE sb_reads (
    read_id           INTEGER PRIMARY KEY,
    artifact_id       INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    items             INTEGER NOT NULL,
    items_recorded    INTEGER NOT NULL,
    already_present   INTEGER NOT NULL,
    items_refused     INTEGER NOT NULL,
    overlaps_previous INTEGER CHECK (overlaps_previous IN (0, 1)),   -- empty for the first read; 0: possible gap
    recorded_at       TEXT NOT NULL
) STRICT;

-- One row per release (one link). The title is data, never instruction (4D).
CREATE TABLE sb_releases (
    release_id  INTEGER PRIMARY KEY,
    link        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    stated_date TEXT NOT NULL,      -- the date SEBI gives; SEBI gives no time of day
    section     TEXT NOT NULL,      -- SEBI's section from the link, e.g. enforcement/orders
    read_id     INTEGER NOT NULL REFERENCES sb_reads(read_id),   -- the first read that carried it
    recorded_at TEXT NOT NULL
) STRICT;

-- Items not stored, and why. Never silently dropped.
CREATE TABLE sb_problems (
    read_id INTEGER NOT NULL REFERENCES sb_reads(read_id),
    kind    TEXT NOT NULL,
    detail  TEXT NOT NULL
) STRICT;

CREATE TRIGGER sb_reads_no_update BEFORE UPDATE ON sb_reads
BEGIN SELECT RAISE(ABORT, 'sb_reads is append-only'); END;
CREATE TRIGGER sb_reads_no_delete BEFORE DELETE ON sb_reads
BEGIN SELECT RAISE(ABORT, 'sb_reads is append-only'); END;
CREATE TRIGGER sb_releases_no_update BEFORE UPDATE ON sb_releases
BEGIN SELECT RAISE(ABORT, 'sb_releases is append-only'); END;
CREATE TRIGGER sb_releases_no_delete BEFORE DELETE ON sb_releases
BEGIN SELECT RAISE(ABORT, 'sb_releases is append-only'); END;
CREATE TRIGGER sb_problems_no_update BEFORE UPDATE ON sb_problems
BEGIN SELECT RAISE(ABORT, 'sb_problems is append-only'); END;
CREATE TRIGGER sb_problems_no_delete BEFORE DELETE ON sb_problems
BEGIN SELECT RAISE(ABORT, 'sb_problems is append-only'); END;
