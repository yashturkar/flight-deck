---
owner: architecture
status: draft
last_verified: 2026-03-07
source_of_truth:
  - ../ARCHITECTURE.md
  - ../../kb-server/BRANCHING_AND_CURRENT_VIEW.md
related_code:
  - ../../kb-server/app/main.py
  - ../../kb-server/app/api/routes/notes.py
  - ../../vault-sync/vault_sync/sync.py
related_tests:
  - ../../kb-server/tests/test_current_view.py
  - ../../vault-sync/tests/test_sync.py
review_cycle_days: 21
---

# Design Docs Index

This index points to durable design guidance used by agents and maintainers.

## Documents

- `core-beliefs.md`: durable principles and invariants.
- `source-map.md`: where doc truth comes from in this monorepo.

## Verification Contract

Each design document must define:

- domain and decision scope
- linked code and tests
- last verification date and review cadence
- explicit superseded/deprecated marker when replaced

## Cross-Links

- Topology: `../../ARCHITECTURE.md`
- Product specs: `../product-specs/index.md`
- Active plans: `../exec-plans/active/context-system-rollout.md`

