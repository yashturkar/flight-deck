---
owner: platform
status: draft
last_verified: 2026-03-07
source_of_truth:
  - ../../kb-server/README.md
  - ../../kb-server/AGENTS.md
  - ../../kb-server/BRANCHING_AND_CURRENT_VIEW.md
  - ../../vault-sync/README.md
related_code:
  - ../../kb-server/app/core/config.py
  - ../../kb-server/app/api/routes/notes.py
  - ../../kb-server/app/services/current_view_service.py
  - ../../vault-sync/vault_sync/config.py
  - ../../vault-sync/vault_sync/sync.py
related_tests:
  - ../../kb-server/tests
  - ../../vault-sync/tests
review_cycle_days: 14
---

# Source Map

This document records where context truth currently lives.

## Existing Seed Docs

- `kb-server/AGENTS.md`: service architecture and workflows.
- `kb-server/README.md`: setup, operations, and API usage.
- `kb-server/BRANCHING_AND_CURRENT_VIEW.md`: branch/view semantics.
- `vault-sync/README.md`: client behavior and service setup.

## Executable Truth

- API contracts and routing: `kb-server/app/api/routes/notes.py`.
- Current-view composition: `kb-server/app/services/current_view_service.py`.
- Sync convergence behavior: `vault-sync/vault_sync/sync.py`.
- Runtime configuration defaults:
  - `kb-server/app/core/config.py`
  - `vault-sync/vault_sync/config.py`

## Drift Risks to Monitor

- Route auth semantics vs README statements.
- Current-view behavior vs high-level branching docs.
- Environment variable tables vs actual settings defaults.
- Sync daemon behavior vs troubleshooting guidance.

## Ownership

- `kb-server` domain docs: backend owner.
- `vault-sync` domain docs: client owner.
- cross-cutting invariants (`AGENTS.md`, `ARCHITECTURE.md`): architecture owner.

