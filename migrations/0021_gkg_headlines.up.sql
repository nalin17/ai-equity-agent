-- Headlines from GDELT's bulk GKG 2.1 files (architecture 40B step 10, 4B, 4D, 5B; ADR-013).
-- A GKG file covers 15 minutes of the world's news (about 4 MB zipped). The raw file is NOT kept: about
-- 0.4 GB a day. Each file read is recorded by its name, size, md5 and sha256 (and GDELT's own md5 when
-- lastupdate.txt listed it); only its India-relevant rows are stored (rule gk-keep-1). Rows are data, never
-- instruction (4D). GDELT's tone is whole-article tone - never sentiment toward a company (4B.5).

-- One row per GKG file read.
CREATE TABLE gk_files (
    file_id       INTEGER PRIMARY KEY,
    file_name     TEXT NOT NULL UNIQUE,        -- YYYYMMDDHHMMSS.gkg.csv.zip, as GDELT names it
    slot_at       TEXT NOT NULL,               -- the file's 15-minute slot, UTC
    size_bytes    INTEGER NOT NULL CHECK (size_bytes > 0),
    md5           TEXT NOT NULL,               -- of the bytes received
    md5_listed    TEXT,                        -- GDELT's md5 from lastupdate.txt when it listed this file, else NULL
    sha256        TEXT NOT NULL,
    retrieved_at  TEXT NOT NULL,
    rows_total    INTEGER NOT NULL,
    rows_kept     INTEGER NOT NULL,            -- India-relevant rows newly stored
    rows_present  INTEGER NOT NULL,            -- India-relevant rows whose link was stored before
    rows_refused  INTEGER NOT NULL,
    keep_rule     TEXT NOT NULL,
    recorded_at   TEXT NOT NULL,
    CHECK (md5_listed IS NULL OR md5_listed = md5)
) STRICT;

-- One row per article link, stored once, from the first file that carried it.
CREATE TABLE gk_articles (
    article_id        INTEGER PRIMARY KEY,
    file_id           INTEGER NOT NULL REFERENCES gk_files(file_id),
    record_id         TEXT NOT NULL,           -- GKGRECORDID
    url               TEXT NOT NULL UNIQUE,
    title             TEXT NOT NULL,           -- PAGE_TITLE verbatim, HTML entities as GDELT wrote them
    source_name       TEXT NOT NULL,           -- SourceCommonName (the outlet's site)
    seen_at           TEXT NOT NULL,           -- GDELT's DATE: the slot, UTC
    available_at      TEXT NOT NULL,           -- seen_at + 15 minutes, or our retrieval if earlier (5B)
    stated_published  TEXT,                    -- PAGE_PRECISEPUBTIMESTAMP verbatim: the page's own claim, not proof
    india_located     INTEGER NOT NULL CHECK (india_located IN (0, 1)),
    indian_outlet     INTEGER NOT NULL CHECK (indian_outlet IN (0, 1)),
    names_declared    INTEGER NOT NULL CHECK (names_declared IN (0, 1)),
    article_tone      REAL NOT NULL,           -- V1.5TONE's first value: WHOLE-ARTICLE tone, never company sentiment
    tone_text         TEXT NOT NULL,           -- V1.5TONE verbatim
    recorded_at       TEXT NOT NULL,
    CHECK (india_located + indian_outlet + names_declared > 0)
) STRICT;
CREATE INDEX gk_articles_seen ON gk_articles (seen_at);

CREATE TABLE gk_problems (
    file_id  INTEGER NOT NULL REFERENCES gk_files(file_id),
    kind     TEXT NOT NULL,
    detail   TEXT NOT NULL
) STRICT;

-- One run of the headline extraction rule with one set of declared news names and one registry state.
CREATE TABLE gk_extraction_runs (
    run_id         INTEGER PRIMARY KEY,
    rule           TEXT NOT NULL,
    reader_version TEXT NOT NULL,
    names_count    INTEGER NOT NULL,
    started_at     TEXT NOT NULL,
    UNIQUE (rule, reader_version)
) STRICT;

-- What a run read from an article's headline and link: the company and its role (rule nw-entity-1).
CREATE TABLE gk_extractions (
    run_id                INTEGER NOT NULL REFERENCES gk_extraction_runs(run_id),
    article_id            INTEGER NOT NULL REFERENCES gk_articles(article_id),
    isin                  TEXT REFERENCES entities(isin),
    role                  TEXT NOT NULL CHECK (role IN ('subject', 'mentioned', 'unassigned')),
    extraction_confidence TEXT NOT NULL CHECK (extraction_confidence IN ('name_in_headline_and_link',
                          'name_in_a_list', 'name_in_headline_only', 'name_in_link_only', 'several_companies_named',
                          'no_name_found')),
    evidence              TEXT NOT NULL,
    extracted_at          TEXT NOT NULL,
    CHECK ((role = 'unassigned') = (isin IS NULL)),
    CHECK ((role = 'unassigned') = (extraction_confidence = 'no_name_found')),
    CHECK ((role = 'subject') = (extraction_confidence = 'name_in_headline_and_link'))
) STRICT;
CREATE INDEX gk_extractions_isin ON gk_extractions (run_id, isin);

CREATE TRIGGER gk_files_no_update BEFORE UPDATE ON gk_files
BEGIN SELECT RAISE(ABORT, 'gk_files is append-only'); END;
CREATE TRIGGER gk_files_no_delete BEFORE DELETE ON gk_files
BEGIN SELECT RAISE(ABORT, 'gk_files is append-only'); END;
CREATE TRIGGER gk_articles_no_update BEFORE UPDATE ON gk_articles
BEGIN SELECT RAISE(ABORT, 'gk_articles is append-only'); END;
CREATE TRIGGER gk_articles_no_delete BEFORE DELETE ON gk_articles
BEGIN SELECT RAISE(ABORT, 'gk_articles is append-only'); END;
CREATE TRIGGER gk_problems_no_update BEFORE UPDATE ON gk_problems
BEGIN SELECT RAISE(ABORT, 'gk_problems is append-only'); END;
CREATE TRIGGER gk_problems_no_delete BEFORE DELETE ON gk_problems
BEGIN SELECT RAISE(ABORT, 'gk_problems is append-only'); END;
CREATE TRIGGER gk_extraction_runs_no_update BEFORE UPDATE ON gk_extraction_runs
BEGIN SELECT RAISE(ABORT, 'gk_extraction_runs is append-only'); END;
CREATE TRIGGER gk_extraction_runs_no_delete BEFORE DELETE ON gk_extraction_runs
BEGIN SELECT RAISE(ABORT, 'gk_extraction_runs is append-only'); END;
CREATE TRIGGER gk_extractions_no_update BEFORE UPDATE ON gk_extractions
BEGIN SELECT RAISE(ABORT, 'gk_extractions is append-only'); END;
CREATE TRIGGER gk_extractions_no_delete BEFORE DELETE ON gk_extractions
BEGIN SELECT RAISE(ABORT, 'gk_extractions is append-only'); END;
