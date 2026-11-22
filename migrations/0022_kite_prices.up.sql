-- Daily NSE equity candles from Zerodha's Kite Connect historical API (architecture 40B step 6a, 4C, 5B; ADR-014).
-- Kite's candles are ADJUSTED for corporate actions by the vendor and re-adjusted after each new split or bonus,
-- so they never enter trusted_prices (raw, as traded): they are kept apart, and every fetch is its own vintage.
-- Kite's terms (4(b)) restrict databases of API content unless Zerodha permits it; the owner chose on 22-Nov-2026
-- to store while Zerodha's written answer is awaited. These tables are append-only for ordinary use; the one
-- way out is purge-kite, which removes ALL Kite data at once (Kite terms 9(b)) - never a row-level edit.
-- No personal data from the login answer (name, email) and no token is ever stored.

-- One row per fetch-kite run.
CREATE TABLE kt_runs (
    run_id               INTEGER PRIMARY KEY,
    started_at           TEXT NOT NULL,
    instruments_listed   INTEGER NOT NULL,   -- NSE EQ instruments in Kite's list that day
    instruments_mapped   INTEGER NOT NULL,   -- of those, matched to a registry company by its NSE symbol
    instruments_sha256   TEXT NOT NULL,      -- of Kite's instrument list as received (the list itself is not kept)
    recorded_at          TEXT NOT NULL
) STRICT;

-- One row per historical answer used: one company, one date range, one vintage.
CREATE TABLE kt_fetches (
    fetch_id          INTEGER PRIMARY KEY,
    run_id            INTEGER NOT NULL REFERENCES kt_runs(run_id),
    isin              TEXT NOT NULL REFERENCES entities(isin),
    tradingsymbol     TEXT NOT NULL,
    instrument_token  INTEGER NOT NULL,
    from_date         TEXT NOT NULL,
    to_date           TEXT NOT NULL,
    retrieved_at      TEXT NOT NULL,
    candles           INTEGER NOT NULL,
    reason            TEXT NOT NULL CHECK (reason IN ('backfill', 'daily', 'readjusted')),
    sha256            TEXT NOT NULL,       -- of the answer as received (the answer itself is not kept)
    recorded_at       TEXT NOT NULL,
    CHECK (from_date <= to_date)
) STRICT;
CREATE INDEX kt_fetches_isin ON kt_fetches (isin, to_date);

-- One row per trading day in one fetch (a vintage of the vendor's adjusted series).
CREATE TABLE kt_candles (
    fetch_id    INTEGER NOT NULL REFERENCES kt_fetches(fetch_id),
    isin        TEXT NOT NULL,
    trade_date  TEXT NOT NULL,
    open        REAL NOT NULL CHECK (open > 0),
    high        REAL NOT NULL CHECK (high > 0),
    low         REAL NOT NULL CHECK (low > 0),
    close       REAL NOT NULL CHECK (close > 0),
    volume      INTEGER NOT NULL CHECK (volume >= 0),
    CHECK (low <= open AND low <= close AND high >= open AND high >= close),
    UNIQUE (fetch_id, trade_date)
) STRICT;
CREATE INDEX kt_candles_day ON kt_candles (isin, trade_date);

-- Symbols in Kite's list that matched no registry company, per run (reported, never guessed).
CREATE TABLE kt_unmapped (
    run_id         INTEGER NOT NULL REFERENCES kt_runs(run_id),
    tradingsymbol  TEXT NOT NULL,
    reason         TEXT NOT NULL
) STRICT;

CREATE TRIGGER kt_runs_no_update BEFORE UPDATE ON kt_runs
BEGIN SELECT RAISE(ABORT, 'kt_runs is append-only'); END;
CREATE TRIGGER kt_runs_no_delete BEFORE DELETE ON kt_runs
BEGIN SELECT RAISE(ABORT, 'kt_runs is append-only - use purge-kite'); END;
CREATE TRIGGER kt_fetches_no_update BEFORE UPDATE ON kt_fetches
BEGIN SELECT RAISE(ABORT, 'kt_fetches is append-only'); END;
CREATE TRIGGER kt_fetches_no_delete BEFORE DELETE ON kt_fetches
BEGIN SELECT RAISE(ABORT, 'kt_fetches is append-only - use purge-kite'); END;
CREATE TRIGGER kt_candles_no_update BEFORE UPDATE ON kt_candles
BEGIN SELECT RAISE(ABORT, 'kt_candles is append-only'); END;
CREATE TRIGGER kt_candles_no_delete BEFORE DELETE ON kt_candles
BEGIN SELECT RAISE(ABORT, 'kt_candles is append-only - use purge-kite'); END;
CREATE TRIGGER kt_unmapped_no_update BEFORE UPDATE ON kt_unmapped
BEGIN SELECT RAISE(ABORT, 'kt_unmapped is append-only'); END;
CREATE TRIGGER kt_unmapped_no_delete BEFORE DELETE ON kt_unmapped
BEGIN SELECT RAISE(ABORT, 'kt_unmapped is append-only - use purge-kite'); END;
