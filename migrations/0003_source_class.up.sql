-- Source class on every registered source (architecture 4F.2, criterion 57).
-- Private tip channels and similar are an EXCLUDED source class: the
-- registry refuses them. SQLite cannot add a NOT NULL column without a
-- permanent default, so the table is rebuilt instead.
-- Every source registered before this migration was an official NSE or
-- NSE Indices declaration; they are marked accordingly. sync_sources then
-- refuses to run if these ever disagree with config/sources.yaml.

CREATE TABLE source_registry_new (
    source_id             TEXT PRIMARY KEY,
    provider              TEXT NOT NULL,
    data_type             TEXT NOT NULL,
    source_class          TEXT NOT NULL,
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

INSERT INTO source_registry_new
SELECT source_id, provider, data_type,
       CASE provider WHEN 'NSE Indices' THEN 'index_provider' ELSE 'exchange_official' END,
       endpoint, authority,
       license, update_frequency, historical_coverage, latency, revision_policy,
       timestamp_semantics, reliability_rating, authentication_method,
       schema_description, registered_at
FROM source_registry;

DROP TABLE source_registry;
ALTER TABLE source_registry_new RENAME TO source_registry;
