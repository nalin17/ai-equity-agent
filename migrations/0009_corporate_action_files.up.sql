-- Loads of NSE's corporate actions file (architecture 6C.2, 4).

CREATE TABLE ca_file_loads (
    load_id           INTEGER PRIMARY KEY,
    artifact_id       INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    parser_version    TEXT NOT NULL,
    rows_in_file      INTEGER NOT NULL,
    rows_out_of_scope INTEGER NOT NULL,
    actions_recorded  INTEGER NOT NULL,
    already_present   INTEGER NOT NULL,
    rejected          INTEGER NOT NULL,
    conflicts         INTEGER NOT NULL,
    recorded_at       TEXT NOT NULL
) STRICT;

-- Rows that could not be attached to a company, and terms that contradict
-- an action already recorded. Kept exactly as received.
CREATE TABLE ca_file_rejections (
    load_id    INTEGER NOT NULL REFERENCES ca_file_loads(load_id),
    row_number INTEGER NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('rejected', 'conflict')),
    reason     TEXT NOT NULL,
    raw_record TEXT NOT NULL
) STRICT;

CREATE TRIGGER ca_file_loads_no_update BEFORE UPDATE ON ca_file_loads
BEGIN SELECT RAISE(ABORT, 'ca_file_loads is append-only'); END;
CREATE TRIGGER ca_file_loads_no_delete BEFORE DELETE ON ca_file_loads
BEGIN SELECT RAISE(ABORT, 'ca_file_loads is append-only'); END;
CREATE TRIGGER ca_file_rejections_no_update BEFORE UPDATE ON ca_file_rejections
BEGIN SELECT RAISE(ABORT, 'ca_file_rejections is append-only'); END;
CREATE TRIGGER ca_file_rejections_no_delete BEFORE DELETE ON ca_file_rejections
BEGIN SELECT RAISE(ABORT, 'ca_file_rejections is append-only'); END;
