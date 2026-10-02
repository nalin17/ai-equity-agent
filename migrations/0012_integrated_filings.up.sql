-- SEBI integrated filings (quarters ended March 2025 onwards): listing and load links
-- (architecture 40B step 7, 5B).

-- One row per filing in NSE's 'Integrated Filing - Financials' listing. The dissemination
-- time is the proven publication time of an Original filing's XBRL file (5B).
CREATE TABLE if_filings (
    filing_id        INTEGER PRIMARY KEY,
    xbrl_file_name   TEXT NOT NULL UNIQUE,
    symbol           TEXT NOT NULL,
    company_name     TEXT NOT NULL,
    quarter_end      TEXT NOT NULL,
    submission_type  TEXT NOT NULL,
    audited          TEXT NOT NULL,
    consolidated     TEXT NOT NULL,
    xbrl_url         TEXT NOT NULL,
    received_at      TEXT NOT NULL,
    disseminated_at  TEXT NOT NULL,
    revised_at       TEXT,
    revision_remarks TEXT,
    artifact_id      INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    recorded_at      TEXT NOT NULL
) STRICT;

-- Which integrated-listing row a results load was checked against.
CREATE TABLE if_load_filings (
    load_id   INTEGER PRIMARY KEY REFERENCES fr_loads(load_id),
    filing_id INTEGER NOT NULL REFERENCES if_filings(filing_id)
) STRICT;

CREATE TRIGGER if_filings_no_update BEFORE UPDATE ON if_filings
BEGIN SELECT RAISE(ABORT, 'if_filings is append-only'); END;
CREATE TRIGGER if_filings_no_delete BEFORE DELETE ON if_filings
BEGIN SELECT RAISE(ABORT, 'if_filings is append-only'); END;
CREATE TRIGGER if_load_filings_no_update BEFORE UPDATE ON if_load_filings
BEGIN SELECT RAISE(ABORT, 'if_load_filings is append-only'); END;
CREATE TRIGGER if_load_filings_no_delete BEFORE DELETE ON if_load_filings
BEGIN SELECT RAISE(ABORT, 'if_load_filings is append-only'); END;
