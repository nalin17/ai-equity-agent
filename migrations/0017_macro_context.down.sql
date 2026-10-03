-- Undo 0017_macro_context.
DROP TRIGGER IF EXISTS mc_problems_no_delete;
DROP TRIGGER IF EXISTS mc_problems_no_update;
DROP TRIGGER IF EXISTS mc_vintages_no_delete;
DROP TRIGGER IF EXISTS mc_vintages_no_update;
DROP TRIGGER IF EXISTS mc_responses_no_delete;
DROP TRIGGER IF EXISTS mc_responses_no_update;
DROP TRIGGER IF EXISTS mc_series_no_delete;
DROP TRIGGER IF EXISTS mc_series_no_update;
DROP TABLE IF EXISTS mc_problems;
DROP TABLE IF EXISTS mc_vintages;
DROP TABLE IF EXISTS mc_responses;
DROP TABLE IF EXISTS mc_series;
