-- Kite day candles set aside (quarantined) inside an answer that is otherwise used (ADR-014, 4C). Found on the
-- owner's first full run, 22-Nov-2026: old SME-period history of some companies has a day candle stamped 10:00
-- instead of 00:00 (SVLL 26-Jun-2018, OSWALSEEDS 12-Jul-2018) or two candles for one day (SONAMLTD 18-Jan-2016,
-- AHLADA 19-Oct-2018). Such a candle is never stored, repaired or chosen between: it is recorded here, and the day
-- stays missing. Removed with every other Kite table by purge-kite.
CREATE TABLE kt_problems (
    fetch_id    INTEGER NOT NULL REFERENCES kt_fetches(fetch_id),
    trade_date  TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('time_not_midnight', 'duplicate_day')),
    detail      TEXT NOT NULL
) STRICT;

CREATE TRIGGER kt_problems_no_update BEFORE UPDATE ON kt_problems
BEGIN SELECT RAISE(ABORT, 'kt_problems is append-only'); END;
CREATE TRIGGER kt_problems_no_delete BEFORE DELETE ON kt_problems
BEGIN SELECT RAISE(ABORT, 'kt_problems is append-only - use purge-kite'); END;
