-- Identity bridges (architecture 6D) and retries of quarantined rows.
--
-- A bridge says: for THIS corporate action only, the security that traded as
-- <symbol> under <old_isin> up to <last_old_date> continues as <new_isin> from
-- <ex_date>. It is evidence-backed and auditable, and asserts nothing about any
-- other event, date or dataset. It never makes two ISINs interchangeable.

CREATE TABLE identity_bridges (
    bridge_id        INTEGER PRIMARY KEY,
    action_id        INTEGER NOT NULL UNIQUE REFERENCES corporate_actions(action_id),
    symbol           TEXT NOT NULL,
    old_isin         TEXT NOT NULL REFERENCES entities(isin),
    new_isin         TEXT NOT NULL REFERENCES entities(isin),
    last_old_date    TEXT NOT NULL,
    ex_date          TEXT NOT NULL,
    old_evidence_run INTEGER NOT NULL REFERENCES ingestion_runs(run_id),
    new_evidence_run INTEGER NOT NULL REFERENCES ingestion_runs(run_id),
    evidence         TEXT NOT NULL,
    bridge_version   TEXT NOT NULL,
    recorded_at      TEXT NOT NULL,
    CHECK (old_isin <> new_isin),
    CHECK (last_old_date < ex_date)
) STRICT;

-- A retry re-runs quarantined rows of an already-stored raw file.
CREATE TABLE retry_runs (
    run_id       INTEGER PRIMARY KEY REFERENCES ingestion_runs(run_id),
    artifact_id  INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    provider     TEXT NOT NULL,
    rows_retried INTEGER NOT NULL,
    reason       TEXT NOT NULL,
    recorded_at  TEXT NOT NULL
) STRICT;

CREATE TRIGGER identity_bridges_no_update BEFORE UPDATE ON identity_bridges
BEGIN SELECT RAISE(ABORT, 'identity_bridges is append-only'); END;
CREATE TRIGGER identity_bridges_no_delete BEFORE DELETE ON identity_bridges
BEGIN SELECT RAISE(ABORT, 'identity_bridges is append-only'); END;
CREATE TRIGGER retry_runs_no_update BEFORE UPDATE ON retry_runs
BEGIN SELECT RAISE(ABORT, 'retry_runs is append-only'); END;
CREATE TRIGGER retry_runs_no_delete BEFORE DELETE ON retry_runs
BEGIN SELECT RAISE(ABORT, 'retry_runs is append-only'); END;
