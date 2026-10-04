-- Macro and geopolitical events (architecture 40B step 9b, 3G, 4A.0, 4A rule 5, 4G, 5B, 5C; ADR-010).
-- Events here have no issuer. They reach a security only through a route declared by the owner and
-- recorded below - never by name, query or guess. Nothing here is a covered security, a target or a
-- benchmark (3G rule 2).

-- One row per kept read of a central bank's official feed.
CREATE TABLE me_reads (
    read_id            INTEGER PRIMARY KEY,
    source_id          TEXT NOT NULL REFERENCES source_registry(source_id),
    artifact_id        INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    items              INTEGER NOT NULL,
    items_recorded     INTEGER NOT NULL,
    already_present    INTEGER NOT NULL,
    items_refused      INTEGER NOT NULL,
    overlaps_previous  INTEGER CHECK (overlaps_previous IN (0, 1)),   -- NULL for a source's first read
    recorded_at        TEXT NOT NULL
) STRICT;

-- One row per feed item, stored once per source by its link.
CREATE TABLE me_items (
    item_id       INTEGER PRIMARY KEY,
    source_id     TEXT NOT NULL REFERENCES source_registry(source_id),
    link          TEXT NOT NULL,
    title         TEXT NOT NULL,          -- verbatim (data, never instruction)
    stated_time   TEXT NOT NULL,          -- the issuer's pubDate exactly as given
    published_at  TEXT NOT NULL,          -- the same instant in UTC; never later than the first read
    read_id       INTEGER NOT NULL REFERENCES me_reads(read_id),   -- the first read that carried it
    recorded_at   TEXT NOT NULL,
    UNIQUE (source_id, link)
) STRICT;

-- Feed items not stored, and why. Never silently dropped.
CREATE TABLE me_problems (
    read_id INTEGER NOT NULL REFERENCES me_reads(read_id),
    kind    TEXT NOT NULL,
    detail  TEXT NOT NULL
) STRICT;

-- One row per kept read of FRED's release calendar for one release.
CREATE TABLE me_calendar_reads (
    read_id       INTEGER PRIMARY KEY,
    release_id    INTEGER NOT NULL,
    artifact_id   INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    dates_listed  INTEGER NOT NULL,
    first_date    TEXT NOT NULL,
    last_date     TEXT NOT NULL,
    changes       INTEGER NOT NULL,       -- dates added or dropped against the previous read
    recorded_at   TEXT NOT NULL
) STRICT;

-- Every date each calendar read listed: a read is a snapshot of the schedule as FRED showed it then.
CREATE TABLE me_calendar_dates (
    read_id       INTEGER NOT NULL REFERENCES me_calendar_reads(read_id),
    release_date  TEXT NOT NULL,
    PRIMARY KEY (read_id, release_date)
) STRICT;

-- Schedule changes found by comparing a read with the previous read of the same release.
CREATE TABLE me_calendar_changes (
    read_id       INTEGER NOT NULL REFERENCES me_calendar_reads(read_id),
    kind          TEXT NOT NULL CHECK (kind IN ('date_added', 'date_dropped')),
    release_date  TEXT NOT NULL
) STRICT;

-- Events declared by the owner (config/declared_events.yaml), recorded once and never silently changed.
CREATE TABLE me_declared (
    event_key     TEXT PRIMARY KEY,
    event_group   TEXT NOT NULL,
    event_type    TEXT NOT NULL,
    region        TEXT NOT NULL,
    institution   TEXT,
    occurred_on   TEXT NOT NULL,
    occurred_at   TEXT,                   -- only when the owner gave a time of day with its zone
    title         TEXT NOT NULL,          -- the owner's own words
    cited_source  TEXT NOT NULL,
    source_url    TEXT,
    declared_on   TEXT NOT NULL,
    entry         TEXT NOT NULL,          -- the whole entry as canonical JSON
    recorded_at   TEXT NOT NULL
) STRICT;

-- Routes declared by the owner (config/event_routes.yaml): the only way an event without an issuer can
-- reach a security (4A rule 5). Only read-across routes can be stored until a point-in-time sector
-- classification (9B) or a measured sensitivity (9C) exists.
CREATE TABLE me_routes (
    route_key     TEXT PRIMARY KEY,
    kind          TEXT NOT NULL CHECK (kind IN ('read_across')),
    event_type    TEXT NOT NULL,
    region        TEXT,                   -- NULL: an event of this type from any region
    isin          TEXT NOT NULL REFERENCES entities(isin),
    relation      TEXT NOT NULL,
    rationale     TEXT NOT NULL,
    valid_from    TEXT NOT NULL,
    declared_on   TEXT NOT NULL,
    entry         TEXT NOT NULL,
    recorded_at   TEXT NOT NULL
) STRICT;

CREATE TRIGGER me_reads_no_update BEFORE UPDATE ON me_reads
BEGIN SELECT RAISE(ABORT, 'me_reads is append-only'); END;
CREATE TRIGGER me_reads_no_delete BEFORE DELETE ON me_reads
BEGIN SELECT RAISE(ABORT, 'me_reads is append-only'); END;
CREATE TRIGGER me_items_no_update BEFORE UPDATE ON me_items
BEGIN SELECT RAISE(ABORT, 'me_items is append-only'); END;
CREATE TRIGGER me_items_no_delete BEFORE DELETE ON me_items
BEGIN SELECT RAISE(ABORT, 'me_items is append-only'); END;
CREATE TRIGGER me_problems_no_update BEFORE UPDATE ON me_problems
BEGIN SELECT RAISE(ABORT, 'me_problems is append-only'); END;
CREATE TRIGGER me_problems_no_delete BEFORE DELETE ON me_problems
BEGIN SELECT RAISE(ABORT, 'me_problems is append-only'); END;
CREATE TRIGGER me_calendar_reads_no_update BEFORE UPDATE ON me_calendar_reads
BEGIN SELECT RAISE(ABORT, 'me_calendar_reads is append-only'); END;
CREATE TRIGGER me_calendar_reads_no_delete BEFORE DELETE ON me_calendar_reads
BEGIN SELECT RAISE(ABORT, 'me_calendar_reads is append-only'); END;
CREATE TRIGGER me_calendar_dates_no_update BEFORE UPDATE ON me_calendar_dates
BEGIN SELECT RAISE(ABORT, 'me_calendar_dates is append-only'); END;
CREATE TRIGGER me_calendar_dates_no_delete BEFORE DELETE ON me_calendar_dates
BEGIN SELECT RAISE(ABORT, 'me_calendar_dates is append-only'); END;
CREATE TRIGGER me_calendar_changes_no_update BEFORE UPDATE ON me_calendar_changes
BEGIN SELECT RAISE(ABORT, 'me_calendar_changes is append-only'); END;
CREATE TRIGGER me_calendar_changes_no_delete BEFORE DELETE ON me_calendar_changes
BEGIN SELECT RAISE(ABORT, 'me_calendar_changes is append-only'); END;
CREATE TRIGGER me_declared_no_update BEFORE UPDATE ON me_declared
BEGIN SELECT RAISE(ABORT, 'me_declared is append-only'); END;
CREATE TRIGGER me_declared_no_delete BEFORE DELETE ON me_declared
BEGIN SELECT RAISE(ABORT, 'me_declared is append-only'); END;
CREATE TRIGGER me_routes_no_update BEFORE UPDATE ON me_routes
BEGIN SELECT RAISE(ABORT, 'me_routes is append-only'); END;
CREATE TRIGGER me_routes_no_delete BEFORE DELETE ON me_routes
BEGIN SELECT RAISE(ABORT, 'me_routes is append-only'); END;
