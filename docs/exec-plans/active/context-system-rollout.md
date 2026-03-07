---
owner: platform
status: active
last_verified: 2026-03-07
source_of_truth:
  - ../../PLANS.md
related_code:
  - ../../../scripts/docs_lint.py
  - ../../../scripts/docs_changed_guard.py
  - ../../../scripts/generate_context_artifacts.py
related_tests:
  - ../../../kb-server/tests
  - ../../../vault-sync/tests
review_cycle_days: 7
---

# Context System Rollout

## Goal

Implement a map-first context system with medium-strength enforcement.

## Scope

- root map docs
- structured docs knowledge base
- docs linter + changed-code guard
- generated context artifacts
- stale-doc gardening workflow

## Decision Log

- 2026-03-07: Selected medium enforcement to avoid noisy failures while reducing drift.
- 2026-03-07: Chose `CLIENTS.md` instead of `FRONTEND.md` to match repository shape.

## Exit Criteria

- all required docs files and indices exist
- docs lint passes in CI
- code-change guard active in PR workflow
- generated docs command is reproducible
- scheduled stale-doc report job exists

---
owner: platform
status: active
last_verified: 2026-03-07
source_of_truth:
  - ../../PLANS.md
related_code:
  - ../../../scripts/docs_lint.py
  - ../../../scripts/docs_changed_guard.py
  - ../../../scripts/generate_context_artifacts.py
related_tests:
  - ../../../kb-server/tests
  - ../../../vault-sync/tests
review_cycle_days: 7
---

# Context System Rollout

## Goal

Implement a map-first context system with medium-strength enforcement.

## Scope

- root map docs
- structured docs knowledge base
- docs linter + changed-code guard
- generated context artifacts
- stale-doc gardening workflow

## Decision Log

- 2026-03-07: Selected medium enforcement to avoid noisy failures while reducing drift.
- 2026-03-07: Chose `CLIENTS.md` instead of `FRONTEND.md` to match repository shape.

## Exit Criteria

- all required docs files and indices exist
- docs lint passes in CI
- code-change guard active in PR workflow
- generated docs command is reproducible
- scheduled stale-doc report job exists

