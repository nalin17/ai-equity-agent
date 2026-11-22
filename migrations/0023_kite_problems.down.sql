-- Undo 0023_kite_problems (also used by purge-kite).
DROP TRIGGER IF EXISTS kt_problems_no_delete;
DROP TRIGGER IF EXISTS kt_problems_no_update;
DROP TABLE IF EXISTS kt_problems;
