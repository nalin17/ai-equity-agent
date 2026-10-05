-- Aggregate investor flows: NSE's daily FII/FPI and DII trading activity in the capital-market segment
-- (architecture 40B step 9c, 3C rule 1, 3G, 4, 4C, 5B; ADR-011). Downloaded by hand (ADR-004). A value is known
-- from this system's ingestion of the file that carried it - never from its trade date. NSE calls the figures
-- provisional; a different value for the same day read later is a new vintage, never an overwrite. A file that
-- breaks any check is refused whole and stores nothing (the intake reports it).

-- One row per ingested file (NSE's page shows only the latest trading day).
CREATE TABLE fl_files (
    file_id      INTEGER PRIMARY KEY,
    artifact_id  INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    scope        TEXT NOT NULL CHECK (scope IN ('nse', 'nse_bse_msei')),
    trade_date   TEXT NOT NULL,
    recorded     INTEGER NOT NULL,      -- values stored from this file (0 when it repeats known values)
    revised      INTEGER NOT NULL,      -- values that differ from what was known for that day
    recorded_at  TEXT NOT NULL
) STRICT;

-- One row per vintage of one category's figures for one trading day.
CREATE TABLE fl_flows (
    flow_id      INTEGER PRIMARY KEY,
    scope        TEXT NOT NULL CHECK (scope IN ('nse', 'nse_bse_msei')),
    trade_date   TEXT NOT NULL,
    category     TEXT NOT NULL CHECK (category IN ('FII/FPI', 'DII')),
    buy_crore    REAL NOT NULL CHECK (buy_crore >= 0),
    sell_crore   REAL NOT NULL CHECK (sell_crore >= 0),
    net_crore    REAL NOT NULL,
    value_text   TEXT NOT NULL,         -- buy, sell and net exactly as NSE wrote them
    file_id      INTEGER NOT NULL REFERENCES fl_files(file_id),
    recorded_at  TEXT NOT NULL
) STRICT;
CREATE INDEX fl_flows_day ON fl_flows (scope, trade_date, category);

CREATE TRIGGER fl_files_no_update BEFORE UPDATE ON fl_files
BEGIN SELECT RAISE(ABORT, 'fl_files is append-only'); END;
CREATE TRIGGER fl_files_no_delete BEFORE DELETE ON fl_files
BEGIN SELECT RAISE(ABORT, 'fl_files is append-only'); END;
CREATE TRIGGER fl_flows_no_update BEFORE UPDATE ON fl_flows
BEGIN SELECT RAISE(ABORT, 'fl_flows is append-only'); END;
CREATE TRIGGER fl_flows_no_delete BEFORE DELETE ON fl_flows
BEGIN SELECT RAISE(ABORT, 'fl_flows is append-only'); END;
