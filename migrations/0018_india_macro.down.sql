-- Undo 0018_india_macro.
DROP TRIGGER IF EXISTS mo_problems_no_delete;
DROP TRIGGER IF EXISTS mo_problems_no_update;
DROP TRIGGER IF EXISTS mo_values_no_delete;
DROP TRIGGER IF EXISTS mo_values_no_update;
DROP TRIGGER IF EXISTS mo_pages_no_delete;
DROP TRIGGER IF EXISTS mo_pages_no_update;
DROP TRIGGER IF EXISTS mo_reads_no_delete;
DROP TRIGGER IF EXISTS mo_reads_no_update;
DROP TRIGGER IF EXISTS mo_series_no_delete;
DROP TRIGGER IF EXISTS mo_series_no_update;
DROP INDEX IF EXISTS mo_values_series_period;
DROP TABLE IF EXISTS mo_problems;
DROP TABLE IF EXISTS mo_values;
DROP TABLE IF EXISTS mo_pages;
DROP TABLE IF EXISTS mo_reads;
DROP TABLE IF EXISTS mo_series;
