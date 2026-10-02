-- Figures corrected by revised filings (architecture 5: a correction is a new version).
-- Each results load records how many stored figures its revision corrected.
ALTER TABLE fr_loads ADD COLUMN facts_corrected INTEGER NOT NULL DEFAULT 0;
