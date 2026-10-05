-- Undo 0020_investor_flows.
DROP TRIGGER IF EXISTS fl_flows_no_delete;
DROP TRIGGER IF EXISTS fl_flows_no_update;
DROP TRIGGER IF EXISTS fl_files_no_delete;
DROP TRIGGER IF EXISTS fl_files_no_update;
DROP INDEX IF EXISTS fl_flows_day;
DROP TABLE IF EXISTS fl_flows;
DROP TABLE IF EXISTS fl_files;
