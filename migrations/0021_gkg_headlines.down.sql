-- Undo 0021_gkg_headlines.
DROP TRIGGER IF EXISTS gk_extractions_no_delete;
DROP TRIGGER IF EXISTS gk_extractions_no_update;
DROP TRIGGER IF EXISTS gk_extraction_runs_no_delete;
DROP TRIGGER IF EXISTS gk_extraction_runs_no_update;
DROP TRIGGER IF EXISTS gk_problems_no_delete;
DROP TRIGGER IF EXISTS gk_problems_no_update;
DROP TRIGGER IF EXISTS gk_articles_no_delete;
DROP TRIGGER IF EXISTS gk_articles_no_update;
DROP TRIGGER IF EXISTS gk_files_no_delete;
DROP TRIGGER IF EXISTS gk_files_no_update;
DROP INDEX IF EXISTS gk_extractions_isin;
DROP INDEX IF EXISTS gk_articles_seen;
DROP TABLE IF EXISTS gk_extractions;
DROP TABLE IF EXISTS gk_extraction_runs;
DROP TABLE IF EXISTS gk_problems;
DROP TABLE IF EXISTS gk_articles;
DROP TABLE IF EXISTS gk_files;
