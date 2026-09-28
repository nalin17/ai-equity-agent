# ADR-001 - Use SQLite instead of DuckDB for now

- decision_id: ADR-001
- date: 2026-09-28
- problem: Architecture Section 38 recommends PostgreSQL / DuckDB. On the
  development machine, Windows Smart App Control blocks the DuckDB library.
- options: (1) turn off Smart App Control - rejected, weakens security and
  cannot easily be re-enabled; (2) PostgreSQL - needs a server install, too
  heavy for Phase A; (3) SQLite - built into Python, nothing to install.
- decision: SQLite, with STRICT tables.
- reason: works now, no install, supports transactional schema migrations.
- impact: all database access goes through src/core/database.py, so a later
  move to DuckDB or PostgreSQL changes one module only.
- supersedes: none
- owner: project owner
