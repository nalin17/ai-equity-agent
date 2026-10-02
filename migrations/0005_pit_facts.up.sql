-- Point-in-time fact store (architecture Sections 5, 4C, 47A guardrail 2,
-- 40A item 12, 40B step 4).
--
-- A fact is never changed. A correction is a NEW version that points at the
-- version it supersedes and cites its evidence. When each version became
-- known comes from its raw artifact (retrieved_at, and published_at if proven).

CREATE TABLE pit_facts (
    fact_id             INTEGER PRIMARY KEY,
    isin                TEXT NOT NULL REFERENCES entities(isin),
    field               TEXT NOT NULL,
    basis               TEXT NOT NULL,
    period_end          TEXT NOT NULL,
    unit                TEXT NOT NULL,
    value               REAL,
    missing_class       TEXT,
    version             INTEGER NOT NULL,
    supersedes_fact_id  INTEGER REFERENCES pit_facts(fact_id),
    correction_evidence TEXT,
    artifact_id         INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    recorded_at         TEXT NOT NULL,
    UNIQUE (isin, field, basis, period_end, version),
    -- 4C rule 1: exactly one of value / missing_class. A bare null is impossible.
    CHECK ((value IS NULL) <> (missing_class IS NULL)),
    -- Version 1 is an original; every later version is a cited correction.
    CHECK ((version = 1) = (supersedes_fact_id IS NULL)),
    CHECK ((version = 1) = (correction_evidence IS NULL))
) STRICT;

CREATE INDEX idx_pit_facts_key ON pit_facts (isin, field, basis, period_end);

-- Guardrail 2: no silent rewriting of history. These tables are append-only.
CREATE TRIGGER pit_facts_no_update BEFORE UPDATE ON pit_facts
BEGIN SELECT RAISE(ABORT, 'pit_facts is append-only: record a correction instead'); END;
CREATE TRIGGER pit_facts_no_delete BEFORE DELETE ON pit_facts
BEGIN SELECT RAISE(ABORT, 'pit_facts is append-only: history is never deleted'); END;

CREATE TRIGGER raw_artifacts_no_update BEFORE UPDATE ON raw_artifacts
BEGIN SELECT RAISE(ABORT, 'raw_artifacts is append-only'); END;
CREATE TRIGGER raw_artifacts_no_delete BEFORE DELETE ON raw_artifacts
BEGIN SELECT RAISE(ABORT, 'raw_artifacts is append-only'); END;

CREATE TRIGGER trusted_prices_no_update BEFORE UPDATE ON trusted_prices
BEGIN SELECT RAISE(ABORT, 'trusted_prices is append-only'); END;
CREATE TRIGGER trusted_prices_no_delete BEFORE DELETE ON trusted_prices
BEGIN SELECT RAISE(ABORT, 'trusted_prices is append-only'); END;

CREATE TRIGGER quarantine_no_update BEFORE UPDATE ON quarantine
BEGIN SELECT RAISE(ABORT, 'quarantine is append-only'); END;
CREATE TRIGGER quarantine_no_delete BEFORE DELETE ON quarantine
BEGIN SELECT RAISE(ABORT, 'quarantine is append-only'); END;

CREATE TRIGGER price_provenance_no_update BEFORE UPDATE ON price_provenance
BEGIN SELECT RAISE(ABORT, 'price_provenance is append-only'); END;
CREATE TRIGGER price_provenance_no_delete BEFORE DELETE ON price_provenance
BEGIN SELECT RAISE(ABORT, 'price_provenance is append-only'); END;
