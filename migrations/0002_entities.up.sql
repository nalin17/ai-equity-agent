-- Entity resolution (architecture Section 4)
-- ISIN is the primary key. Symbols, scrip codes and names are aliases,
-- each valid for a date range. Renames and mergers are events, never
-- overwrites.

CREATE TABLE entities (
    isin        TEXT PRIMARY KEY,
    legal_name  TEXT NOT NULL,
    recorded_at TEXT NOT NULL
) STRICT;

CREATE TABLE entity_aliases (
    alias_id    INTEGER PRIMARY KEY,
    isin        TEXT NOT NULL REFERENCES entities(isin),
    alias_type  TEXT NOT NULL,
    alias_value TEXT NOT NULL,
    valid_from  TEXT NOT NULL,
    valid_to    TEXT,            -- empty (NULL) means still valid
    recorded_at TEXT NOT NULL
) STRICT;

CREATE INDEX idx_alias_lookup ON entity_aliases (alias_value, alias_type);

CREATE TABLE entity_events (
    event_id       INTEGER PRIMARY KEY,
    isin           TEXT NOT NULL REFERENCES entities(isin),
    event_type     TEXT NOT NULL,
    related_isin   TEXT REFERENCES entities(isin),
    effective_date TEXT NOT NULL,
    details        TEXT NOT NULL,
    recorded_at    TEXT NOT NULL
) STRICT;
