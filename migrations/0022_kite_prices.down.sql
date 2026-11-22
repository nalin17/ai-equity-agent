-- Undo 0022_kite_prices (also used by purge-kite, followed by the up script, to remove all Kite data).
DROP TRIGGER IF EXISTS kt_unmapped_no_delete;
DROP TRIGGER IF EXISTS kt_unmapped_no_update;
DROP TRIGGER IF EXISTS kt_candles_no_delete;
DROP TRIGGER IF EXISTS kt_candles_no_update;
DROP TRIGGER IF EXISTS kt_fetches_no_delete;
DROP TRIGGER IF EXISTS kt_fetches_no_update;
DROP TRIGGER IF EXISTS kt_runs_no_delete;
DROP TRIGGER IF EXISTS kt_runs_no_update;
DROP INDEX IF EXISTS kt_candles_day;
DROP INDEX IF EXISTS kt_fetches_isin;
DROP TABLE IF EXISTS kt_unmapped;
DROP TABLE IF EXISTS kt_candles;
DROP TABLE IF EXISTS kt_fetches;
DROP TABLE IF EXISTS kt_runs;
