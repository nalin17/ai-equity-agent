-- NSE corporate announcements: one row per filing (architecture 40B step 8, 4A, 5B).
-- Events are derived from these filings by a versioned rule (4A rule 2); they are not stored.

CREATE TABLE an_filings (
    filing_id       INTEGER PRIMARY KEY,
    isin            TEXT NOT NULL REFERENCES entities(isin),
    symbol          TEXT NOT NULL,
    company_name    TEXT NOT NULL,
    subject         TEXT NOT NULL,
    details         TEXT NOT NULL,
    received_at     TEXT NOT NULL,
    disseminated_at TEXT NOT NULL,
    attachment_url  TEXT NOT NULL,
    attachment_name TEXT,
    artifact_id     INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    recorded_at     TEXT NOT NULL,
    UNIQUE (symbol, received_at, subject, attachment_url, details)
) STRICT;
CREATE INDEX an_filings_isin_time ON an_filings (isin, disseminated_at);

-- One row per listing file loaded.
CREATE TABLE an_loads (
    load_id          INTEGER PRIMARY KEY,
    artifact_id      INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    rows_in_file     INTEGER NOT NULL,
    filings_recorded INTEGER NOT NULL,
    already_present  INTEGER NOT NULL,
    rows_refused     INTEGER NOT NULL,
    recorded_at      TEXT NOT NULL
) STRICT;

-- Rows not stored, and why. Never silently dropped.
CREATE TABLE an_problems (
    load_id INTEGER NOT NULL REFERENCES an_loads(load_id),
    kind    TEXT NOT NULL,
    detail  TEXT NOT NULL
) STRICT;

CREATE TRIGGER an_filings_no_update BEFORE UPDATE ON an_filings
BEGIN SELECT RAISE(ABORT, 'an_filings is append-only'); END;
CREATE TRIGGER an_filings_no_delete BEFORE DELETE ON an_filings
BEGIN SELECT RAISE(ABORT, 'an_filings is append-only'); END;
CREATE TRIGGER an_loads_no_update BEFORE UPDATE ON an_loads
BEGIN SELECT RAISE(ABORT, 'an_loads is append-only'); END;
CREATE TRIGGER an_loads_no_delete BEFORE DELETE ON an_loads
BEGIN SELECT RAISE(ABORT, 'an_loads is append-only'); END;
CREATE TRIGGER an_problems_no_update BEFORE UPDATE ON an_problems
BEGIN SELECT RAISE(ABORT, 'an_problems is append-only'); END;
CREATE TRIGGER an_problems_no_delete BEFORE DELETE ON an_problems
BEGIN SELECT RAISE(ABORT, 'an_problems is append-only'); END;
