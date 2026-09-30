-- Source Registry (architecture Section 4, 40B step 2)
CREATE TABLE source_registry (
    source_id             TEXT PRIMARY KEY,
    provider              TEXT NOT NULL,
    data_type             TEXT NOT NULL,
    endpoint              TEXT NOT NULL,
    authority             TEXT NOT NULL,
    license               TEXT NOT NULL,
    update_frequency      TEXT NOT NULL,
    historical_coverage   TEXT NOT NULL,
    latency               TEXT NOT NULL,
    revision_policy       TEXT NOT NULL,
    timestamp_semantics   TEXT NOT NULL,
    reliability_rating    TEXT NOT NULL,
    authentication_method TEXT NOT NULL,
    schema_description    TEXT NOT NULL,
    registered_at         TEXT NOT NULL
) STRICT;
