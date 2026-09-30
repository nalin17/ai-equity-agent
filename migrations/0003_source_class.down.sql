CREATE TABLE source_registry_old (
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

INSERT INTO source_registry_old
SELECT source_id, provider, data_type, endpoint, authority, license,
       update_frequency, historical_coverage, latency, revision_policy,
       timestamp_semantics, reliability_rating, authentication_method,
       schema_description, registered_at
FROM source_registry;

DROP TABLE source_registry;
ALTER TABLE source_registry_old RENAME TO source_registry;
