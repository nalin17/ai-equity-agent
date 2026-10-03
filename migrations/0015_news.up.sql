-- News from GDELT (architecture 40B step 9, 4A, 4B.4, 4D, 5B; ADR-005).
-- Articles are stored once; which company an article is about is an extraction with its own
-- extraction confidence (4A rule 4). Investment confidence is never stored with news.
-- Copies of one story are derived by a versioned rule (4A rule 2); they are not stored.

-- One row per GDELT response kept.
CREATE TABLE nw_responses (
    response_id      INTEGER PRIMARY KEY,
    artifact_id      INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    isin             TEXT NOT NULL REFERENCES entities(isin),   -- the company the search was for
    query            TEXT NOT NULL,
    window_start     TEXT NOT NULL,
    window_end       TEXT NOT NULL,
    articles         INTEGER NOT NULL,
    complete         INTEGER NOT NULL CHECK (complete IN (0, 1)),   -- 0: GDELT's cap may have cut it
    articles_recorded INTEGER NOT NULL,
    already_present  INTEGER NOT NULL,
    articles_refused INTEGER NOT NULL,
    recorded_at      TEXT NOT NULL
) STRICT;

-- One row per article (one link). The headline is data, never instruction (4D).
CREATE TABLE nw_articles (
    article_id     INTEGER PRIMARY KEY,
    url            TEXT NOT NULL UNIQUE,
    title          TEXT NOT NULL,
    domain         TEXT NOT NULL,
    language       TEXT NOT NULL,
    source_country TEXT NOT NULL,
    seen_at        TEXT NOT NULL,      -- when GDELT first saw it
    available_at   TEXT NOT NULL,      -- proven public by then (5B): seen_at + 15 minutes, or our retrieval if earlier
    response_id    INTEGER NOT NULL REFERENCES nw_responses(response_id),   -- the first response that carried it
    recorded_at    TEXT NOT NULL
) STRICT;
CREATE INDEX nw_articles_available ON nw_articles (available_at);

-- Every response that returned an article (the search context of an article, 4B.4).
CREATE TABLE nw_retrievals (
    response_id INTEGER NOT NULL REFERENCES nw_responses(response_id),
    article_id  INTEGER NOT NULL REFERENCES nw_articles(article_id),
    PRIMARY KEY (response_id, article_id)
) STRICT;

-- Articles not stored, and why. Never silently dropped.
CREATE TABLE nw_problems (
    response_id INTEGER NOT NULL REFERENCES nw_responses(response_id),
    kind        TEXT NOT NULL,
    detail      TEXT NOT NULL
) STRICT;

-- One run of an extraction rule with one set of declared news names.
CREATE TABLE nw_extraction_runs (
    run_id        INTEGER PRIMARY KEY,
    rule          TEXT NOT NULL,
    reader_version TEXT NOT NULL,
    names_count   INTEGER NOT NULL,
    started_at    TEXT NOT NULL,
    UNIQUE (rule, reader_version)
) STRICT;

-- What a run read from an article: the company and its role, with extraction confidence.
CREATE TABLE nw_extractions (
    run_id                INTEGER NOT NULL REFERENCES nw_extraction_runs(run_id),
    article_id            INTEGER NOT NULL REFERENCES nw_articles(article_id),
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
CREATE UNIQUE INDEX nw_extractions_company ON nw_extractions (run_id, article_id, isin) WHERE isin IS NOT NULL;
CREATE UNIQUE INDEX nw_extractions_unassigned ON nw_extractions (run_id, article_id) WHERE isin IS NULL;
CREATE INDEX nw_extractions_isin ON nw_extractions (isin, run_id);

CREATE TRIGGER nw_responses_no_update BEFORE UPDATE ON nw_responses
BEGIN SELECT RAISE(ABORT, 'nw_responses is append-only'); END;
CREATE TRIGGER nw_responses_no_delete BEFORE DELETE ON nw_responses
BEGIN SELECT RAISE(ABORT, 'nw_responses is append-only'); END;
CREATE TRIGGER nw_articles_no_update BEFORE UPDATE ON nw_articles
BEGIN SELECT RAISE(ABORT, 'nw_articles is append-only'); END;
CREATE TRIGGER nw_articles_no_delete BEFORE DELETE ON nw_articles
BEGIN SELECT RAISE(ABORT, 'nw_articles is append-only'); END;
CREATE TRIGGER nw_retrievals_no_update BEFORE UPDATE ON nw_retrievals
BEGIN SELECT RAISE(ABORT, 'nw_retrievals is append-only'); END;
CREATE TRIGGER nw_retrievals_no_delete BEFORE DELETE ON nw_retrievals
BEGIN SELECT RAISE(ABORT, 'nw_retrievals is append-only'); END;
CREATE TRIGGER nw_problems_no_update BEFORE UPDATE ON nw_problems
BEGIN SELECT RAISE(ABORT, 'nw_problems is append-only'); END;
CREATE TRIGGER nw_problems_no_delete BEFORE DELETE ON nw_problems
BEGIN SELECT RAISE(ABORT, 'nw_problems is append-only'); END;
CREATE TRIGGER nw_extraction_runs_no_update BEFORE UPDATE ON nw_extraction_runs
BEGIN SELECT RAISE(ABORT, 'nw_extraction_runs is append-only'); END;
CREATE TRIGGER nw_extraction_runs_no_delete BEFORE DELETE ON nw_extraction_runs
BEGIN SELECT RAISE(ABORT, 'nw_extraction_runs is append-only'); END;
CREATE TRIGGER nw_extractions_no_update BEFORE UPDATE ON nw_extractions
BEGIN SELECT RAISE(ABORT, 'nw_extractions is append-only'); END;
CREATE TRIGGER nw_extractions_no_delete BEFORE DELETE ON nw_extractions
BEGIN SELECT RAISE(ABORT, 'nw_extractions is append-only'); END;
