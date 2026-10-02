-- Data Trust chain (architecture Section 4, 4C.1, 5B, 40A item 11, 40B step 3)

-- Every downloaded file is kept byte-for-byte, identified by its SHA-256 hash.
-- published_at is filled only when the publication time is PROVEN; the
-- evidence for it is then mandatory. Otherwise both stay empty.
CREATE TABLE raw_artifacts (
    artifact_id          INTEGER PRIMARY KEY,
    source_id            TEXT NOT NULL REFERENCES source_registry(source_id),
    sha256               TEXT NOT NULL UNIQUE,
    original_name        TEXT NOT NULL,
    stored_path          TEXT NOT NULL,
    byte_size            INTEGER NOT NULL,
    retrieved_at         TEXT NOT NULL,
    published_at         TEXT,
    publication_evidence TEXT,
    recorded_at          TEXT NOT NULL,
    CHECK ((published_at IS NULL) = (publication_evidence IS NULL))
) STRICT;

-- One row per time a file is pushed through the trust chain.
CREATE TABLE ingestion_runs (
    run_id           INTEGER PRIMARY KEY,
    artifact_id      INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    pipeline_version TEXT NOT NULL,
    rows_total       INTEGER NOT NULL,
    rows_trusted     INTEGER NOT NULL,
    rows_duplicate   INTEGER NOT NULL,
    rows_quarantined INTEGER NOT NULL,
    recorded_at      TEXT NOT NULL
) STRICT;

-- Records that failed a trust stage. Kept exactly as received, never repaired.
CREATE TABLE quarantine (
    quarantine_id INTEGER PRIMARY KEY,
    run_id        INTEGER NOT NULL REFERENCES ingestion_runs(run_id),
    row_number    INTEGER NOT NULL,
    failed_stage  TEXT NOT NULL,
    reason        TEXT NOT NULL,
    raw_record    TEXT NOT NULL,
    recorded_at   TEXT NOT NULL
) STRICT;

-- Daily prices that passed every stage. One fact per security per day.
CREATE TABLE trusted_prices (
    price_id     INTEGER PRIMARY KEY,
    isin         TEXT NOT NULL REFERENCES entities(isin),
    trade_date   TEXT NOT NULL,
    open_price   REAL NOT NULL,
    high_price   REAL NOT NULL,
    low_price    REAL NOT NULL,
    close_price  REAL NOT NULL,
    volume       INTEGER NOT NULL,
    first_run_id INTEGER NOT NULL REFERENCES ingestion_runs(run_id),
    recorded_at  TEXT NOT NULL,
    UNIQUE (isin, trade_date)
) STRICT;

-- Where each trusted price came from. The same fact arriving twice is one
-- fact with two provenance rows, not two facts (Section 4).
CREATE TABLE price_provenance (
    price_id   INTEGER NOT NULL REFERENCES trusted_prices(price_id),
    run_id     INTEGER NOT NULL REFERENCES ingestion_runs(run_id),
    row_number INTEGER NOT NULL,
    PRIMARY KEY (price_id, run_id, row_number)
) STRICT;
