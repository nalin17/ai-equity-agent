-- India macro context from MoSPI's eSankhyiki API (architecture 40B step 9a, 3G, 5A.1, 5B; ADR-009).
-- MoSPI gives no publication time and no revision marks: a value is known from this system's first read of
-- it, and a changed value read later is a new vintage. Nothing here is a covered security, a target or a
-- benchmark (3G rule 2).

-- The registered series (config/india_macro_series.yaml), recorded once and never silently changed.
CREATE TABLE mo_series (
    series_id     TEXT PRIMARY KEY,
    source_id     TEXT NOT NULL REFERENCES source_registry(source_id),
    title         TEXT NOT NULL,
    factor_group  TEXT NOT NULL,
    dataset       TEXT NOT NULL CHECK (dataset IN ('cpi', 'iip', 'nas')),
    request       TEXT NOT NULL,      -- the filters sent, as canonical JSON
    expect        TEXT NOT NULL,      -- the fields every row must carry, as canonical JSON
    row_select    TEXT NOT NULL,      -- the fields that pick the aggregate row, as canonical JSON
    measure       TEXT NOT NULL,
    unit          TEXT NOT NULL,
    frequency     TEXT NOT NULL CHECK (frequency IN ('monthly', 'quarterly')),
    status        TEXT NOT NULL CHECK (status IN ('published', 'reconstructed')),
    publisher     TEXT NOT NULL,
    licence       TEXT NOT NULL,
    recorded_at   TEXT NOT NULL
) STRICT;

-- One row per complete read of one request (all its pages) that was kept.
CREATE TABLE mo_reads (
    read_id            INTEGER PRIMARY KEY,
    dataset            TEXT NOT NULL,
    request            TEXT NOT NULL,
    pages              INTEGER NOT NULL,
    rows               INTEGER NOT NULL,
    retrieved_at       TEXT NOT NULL,     -- when the last page was read: every value was known by then
    values_recorded    INTEGER NOT NULL,
    already_present    INTEGER NOT NULL,
    problems           INTEGER NOT NULL,
    recorded_at        TEXT NOT NULL
) STRICT;

-- The raw page files of each read (an unchanged page is shared with the read that first stored it).
CREATE TABLE mo_pages (
    read_id      INTEGER NOT NULL REFERENCES mo_reads(read_id),
    page         INTEGER NOT NULL,
    artifact_id  INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    PRIMARY KEY (read_id, page)
) STRICT;

-- One row per vintage: a value for a period as first seen by a read.
CREATE TABLE mo_values (
    value_id     INTEGER PRIMARY KEY,
    series_id    TEXT NOT NULL REFERENCES mo_series(series_id),
    period       TEXT NOT NULL,          -- first day of the month or of the financial-year quarter
    value        REAL NOT NULL,
    value_text   TEXT NOT NULL,          -- exactly as MoSPI gave it
    read_id      INTEGER NOT NULL REFERENCES mo_reads(read_id),
    recorded_at  TEXT NOT NULL
) STRICT;
CREATE INDEX mo_values_series_period ON mo_values (series_id, period);

-- Rows not stored, and why. Never silently dropped.
CREATE TABLE mo_problems (
    read_id INTEGER NOT NULL REFERENCES mo_reads(read_id),
    kind    TEXT NOT NULL,
    detail  TEXT NOT NULL
) STRICT;

CREATE TRIGGER mo_series_no_update BEFORE UPDATE ON mo_series
BEGIN SELECT RAISE(ABORT, 'mo_series is append-only'); END;
CREATE TRIGGER mo_series_no_delete BEFORE DELETE ON mo_series
BEGIN SELECT RAISE(ABORT, 'mo_series is append-only'); END;
CREATE TRIGGER mo_reads_no_update BEFORE UPDATE ON mo_reads
BEGIN SELECT RAISE(ABORT, 'mo_reads is append-only'); END;
CREATE TRIGGER mo_reads_no_delete BEFORE DELETE ON mo_reads
BEGIN SELECT RAISE(ABORT, 'mo_reads is append-only'); END;
CREATE TRIGGER mo_pages_no_update BEFORE UPDATE ON mo_pages
BEGIN SELECT RAISE(ABORT, 'mo_pages is append-only'); END;
CREATE TRIGGER mo_pages_no_delete BEFORE DELETE ON mo_pages
BEGIN SELECT RAISE(ABORT, 'mo_pages is append-only'); END;
CREATE TRIGGER mo_values_no_update BEFORE UPDATE ON mo_values
BEGIN SELECT RAISE(ABORT, 'mo_values is append-only'); END;
CREATE TRIGGER mo_values_no_delete BEFORE DELETE ON mo_values
BEGIN SELECT RAISE(ABORT, 'mo_values is append-only'); END;
CREATE TRIGGER mo_problems_no_update BEFORE UPDATE ON mo_problems
BEGIN SELECT RAISE(ABORT, 'mo_problems is append-only'); END;
CREATE TRIGGER mo_problems_no_delete BEFORE DELETE ON mo_problems
BEGIN SELECT RAISE(ABORT, 'mo_problems is append-only'); END;
