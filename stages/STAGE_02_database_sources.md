# Stage 2 - Database and Source Registry

Built: src/core/database.py (SQLite, numbered reversible migrations),
src/ingestion/source_registry.py (refuses incomplete, invalid or duplicate
sources), config/sources.yaml (3 NSE sources declared), manage.py,
docs/decisions/ADR-001-sqlite.md.
Architecture: Section 4 Source Registry; 40A item 5; 40B step 2; Section 45.
Test: `python -m pytest -v` -> 19 passed. `python manage.py init-db` twice ->
second run registers nothing new.
