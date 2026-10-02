-- Market data adapters and the NSE equity list (architecture 40A item 7, 40B step 6, 40G.2).

-- Which provider format each price file was read with, and what was left out
-- of scope (for example non-EQ series). Out-of-scope rows are not defects.
CREATE TABLE adapter_runs (
    run_id            INTEGER PRIMARY KEY REFERENCES ingestion_runs(run_id),
    provider          TEXT NOT NULL,
    provider_version  TEXT NOT NULL,
    rows_in_file      INTEGER NOT NULL,
    rows_out_of_scope INTEGER NOT NULL,
    scope_rule        TEXT NOT NULL,
    recorded_at       TEXT NOT NULL
) STRICT;

-- Each load of NSE's list of listed securities (a current snapshot).
CREATE TABLE entity_list_loads (
    load_id         INTEGER PRIMARY KEY,
    artifact_id     INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    rows_in_file    INTEGER NOT NULL,
    entities_added  INTEGER NOT NULL,
    already_present INTEGER NOT NULL,
    rejected        INTEGER NOT NULL,
    recorded_at     TEXT NOT NULL
) STRICT;

-- Rows of that list that could not be used, kept exactly as received.
CREATE TABLE entity_list_rejections (
    load_id    INTEGER NOT NULL REFERENCES entity_list_loads(load_id),
    row_number INTEGER NOT NULL,
    reason     TEXT NOT NULL,
    raw_record TEXT NOT NULL
) STRICT;

CREATE TRIGGER adapter_runs_no_update BEFORE UPDATE ON adapter_runs
BEGIN SELECT RAISE(ABORT, 'adapter_runs is append-only'); END;
CREATE TRIGGER adapter_runs_no_delete BEFORE DELETE ON adapter_runs
BEGIN SELECT RAISE(ABORT, 'adapter_runs is append-only'); END;
CREATE TRIGGER entity_list_loads_no_update BEFORE UPDATE ON entity_list_loads
BEGIN SELECT RAISE(ABORT, 'entity_list_loads is append-only'); END;
CREATE TRIGGER entity_list_loads_no_delete BEFORE DELETE ON entity_list_loads
BEGIN SELECT RAISE(ABORT, 'entity_list_loads is append-only'); END;
CREATE TRIGGER entity_list_rejections_no_update BEFORE UPDATE ON entity_list_rejections
BEGIN SELECT RAISE(ABORT, 'entity_list_rejections is append-only'); END;
CREATE TRIGGER entity_list_rejections_no_delete BEFORE DELETE ON entity_list_rejections
BEGIN SELECT RAISE(ABORT, 'entity_list_rejections is append-only'); END;
