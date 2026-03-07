---
owner: sre
status: draft
last_verified: 2026-03-07
source_of_truth:
  - ../../kb-server/README.md
related_code:
  - ../../kb-server/alembic/versions/001_initial_tables.py
related_tests:
  - ../../kb-server/tests
review_cycle_days: 30
---

# Backup and Restore Runbook

## Backup Policy

- Vault content is backed by Git remote history.
- DB metadata is backed up using `pg_dump`.
- Service configuration files are managed in repository + deployment env.

## Restore Steps

1. Restore vault checkout from Git remote.
2. Restore database using `pg_restore`.
3. Run migrations to target version.
4. Validate readiness and end-to-end write/read flows.

## Verification

- Sample read from `view=main` and `view=current`.
- One `source=human` write and one `source=api` write path test.

