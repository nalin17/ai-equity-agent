-- Global and India macro context from FRED/ALFRED (architecture 40B step 9a, 3G, 5, 5A, 5B, 5C; ADR-008).
-- Every value is kept as a vintage: what FRED showed for a date from a given real-time start. A revision is
-- a new vintage, never an overwrite. Nothing here is a covered security, a target or a benchmark (3G rule 2).

-- The registered series (config/macro_series.yaml), recorded once and never silently changed.
CREATE TABLE mc_series (
    series_id      TEXT PRIMARY KEY,
    source_id      TEXT NOT NULL REFERENCES source_registry(source_id),
    title          TEXT NOT NULL,
    factor_group   TEXT NOT NULL,
    region         TEXT NOT NULL,
    kind           TEXT NOT NULL CHECK (kind IN ('market_close', 'published_statistic')),
    market         TEXT NOT NULL,      -- the exchange that sets it, or the publisher that compiles it
    calendar       TEXT NOT NULL,      -- which days carry a value
    time_zone      TEXT NOT NULL,
    session_close  TEXT,               -- HH:MM local time, market closes only
    frequency      TEXT NOT NULL CHECK (frequency IN ('daily', 'daily_7day', 'weekly', 'monthly', 'quarterly')),
    fred_units     TEXT NOT NULL,      -- FRED's own description of the units, checked on every answer
    history_from   TEXT NOT NULL,
    licence        TEXT NOT NULL,
    recorded_at    TEXT NOT NULL,
    CHECK ((kind = 'market_close') = (session_close IS NOT NULL))
) STRICT;

-- One row per FRED answer that was kept: the observations answer and the series description read
-- right after it. The request is stored without the key (4G rule 5).
CREATE TABLE mc_responses (
    response_id        INTEGER PRIMARY KEY,
    series_id          TEXT NOT NULL REFERENCES mc_series(series_id),
    artifact_id        INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),   -- the observations
    meta_artifact_id   INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),   -- the series description
    request            TEXT NOT NULL,
    meta_retrieved_at  TEXT NOT NULL,
    series_updated_at  TEXT NOT NULL,   -- FRED's last update of the series, as FRED states it
    rows               INTEGER NOT NULL,
    vintages_recorded  INTEGER NOT NULL,
    already_present    INTEGER NOT NULL,
    rows_refused       INTEGER NOT NULL,
    recorded_at        TEXT NOT NULL
) STRICT;

-- One row per vintage of one observation.
CREATE TABLE mc_vintages (
    vintage_id      INTEGER PRIMARY KEY,
    series_id       TEXT NOT NULL REFERENCES mc_series(series_id),
    obs_date        TEXT NOT NULL,
    value           REAL,
    missing_class   TEXT CHECK (missing_class IN ('structurally_absent')),
    value_text      TEXT NOT NULL,      -- exactly as FRED gave it, e.g. '4.97' or '.'
    realtime_start  TEXT NOT NULL,      -- ALFRED: the first day FRED showed this value
    start_clipped   INTEGER NOT NULL CHECK (start_clipped IN (0, 1)),   -- 1: the true start is this day or earlier
    set_at          TEXT,               -- market closes: the session close in UTC
    available_at    TEXT NOT NULL,      -- proven: in FRED by FRED's last update before our read
    response_id     INTEGER NOT NULL REFERENCES mc_responses(response_id),   -- the first answer that carried it
    recorded_at     TEXT NOT NULL,
    UNIQUE (series_id, obs_date, realtime_start),
    CHECK ((value IS NULL) <> (missing_class IS NULL)),
    CHECK (set_at IS NULL OR set_at <= available_at)
) STRICT;

-- Rows not stored, and why. Never silently dropped.
CREATE TABLE mc_problems (
    response_id INTEGER NOT NULL REFERENCES mc_responses(response_id),
    kind        TEXT NOT NULL,
    detail      TEXT NOT NULL
) STRICT;

CREATE TRIGGER mc_series_no_update BEFORE UPDATE ON mc_series
BEGIN SELECT RAISE(ABORT, 'mc_series is append-only'); END;
CREATE TRIGGER mc_series_no_delete BEFORE DELETE ON mc_series
BEGIN SELECT RAISE(ABORT, 'mc_series is append-only'); END;
CREATE TRIGGER mc_responses_no_update BEFORE UPDATE ON mc_responses
BEGIN SELECT RAISE(ABORT, 'mc_responses is append-only'); END;
CREATE TRIGGER mc_responses_no_delete BEFORE DELETE ON mc_responses
BEGIN SELECT RAISE(ABORT, 'mc_responses is append-only'); END;
CREATE TRIGGER mc_vintages_no_update BEFORE UPDATE ON mc_vintages
BEGIN SELECT RAISE(ABORT, 'mc_vintages is append-only'); END;
CREATE TRIGGER mc_vintages_no_delete BEFORE DELETE ON mc_vintages
BEGIN SELECT RAISE(ABORT, 'mc_vintages is append-only'); END;
CREATE TRIGGER mc_problems_no_update BEFORE UPDATE ON mc_problems
BEGIN SELECT RAISE(ABORT, 'mc_problems is append-only'); END;
CREATE TRIGGER mc_problems_no_delete BEFORE DELETE ON mc_problems
BEGIN SELECT RAISE(ABORT, 'mc_problems is append-only'); END;
