-- NSE financial results: filing listing and XBRL loads (architecture 40B step 7, 5B, 4).

-- One row per filing in NSE's results listing. The dissemination time is the
-- proven publication time of that filing's XBRL file (5B).
CREATE TABLE fr_filings (
    filing_id       INTEGER PRIMARY KEY,
    xbrl_file_name  TEXT NOT NULL UNIQUE,
    company_name    TEXT NOT NULL,
    audited         TEXT NOT NULL,
    cumulative      TEXT NOT NULL,
    consolidated    TEXT NOT NULL,
    period          TEXT NOT NULL,
    period_ended    TEXT NOT NULL,
    xbrl_url        TEXT NOT NULL,
    received_at     TEXT NOT NULL,
    disseminated_at TEXT NOT NULL,
    artifact_id     INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    recorded_at     TEXT NOT NULL
) STRICT;

-- One row per XBRL file loaded.
CREATE TABLE fr_loads (
    load_id            INTEGER PRIMARY KEY,
    artifact_id        INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    parser_version     TEXT NOT NULL,
    isin               TEXT NOT NULL REFERENCES entities(isin),
    symbol             TEXT NOT NULL,
    basis              TEXT NOT NULL,
    audited            TEXT NOT NULL,
    filing_id          INTEGER REFERENCES fr_filings(filing_id),
    facts_recorded     INTEGER NOT NULL,
    facts_already_present INTEGER NOT NULL,
    facts_marked_conflict INTEGER NOT NULL,
    problems           INTEGER NOT NULL,
    recorded_at        TEXT NOT NULL
) STRICT;

-- What was not stored, and why. Never silently dropped.
CREATE TABLE fr_problems (
    load_id INTEGER REFERENCES fr_loads(load_id),
    kind    TEXT NOT NULL,
    detail  TEXT NOT NULL
) STRICT;

CREATE TRIGGER fr_filings_no_update BEFORE UPDATE ON fr_filings
BEGIN SELECT RAISE(ABORT, 'fr_filings is append-only'); END;
CREATE TRIGGER fr_filings_no_delete BEFORE DELETE ON fr_filings
BEGIN SELECT RAISE(ABORT, 'fr_filings is append-only'); END;
CREATE TRIGGER fr_loads_no_update BEFORE UPDATE ON fr_loads
BEGIN SELECT RAISE(ABORT, 'fr_loads is append-only'); END;
CREATE TRIGGER fr_loads_no_delete BEFORE DELETE ON fr_loads
BEGIN SELECT RAISE(ABORT, 'fr_loads is append-only'); END;
CREATE TRIGGER fr_problems_no_update BEFORE UPDATE ON fr_problems
BEGIN SELECT RAISE(ABORT, 'fr_problems is append-only'); END;
CREATE TRIGGER fr_problems_no_delete BEFORE DELETE ON fr_problems
BEGIN SELECT RAISE(ABORT, 'fr_problems is append-only'); END;
