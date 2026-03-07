---
owner: platform
status: verified
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
review_cycle_days: 30
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
- 2026-03-07: Closed rollout and moved execution record to completed plans.

## Exit Criteria Evidence

- Required docs/indices exist and are linted by `python3 scripts/docs_lint.py`.
- Docs lint runs in PR CI via `.github/workflows/docs-context.yml`.
- Code-change guard runs in PR CI via `python3 scripts/docs_changed_guard.py` in `.github/workflows/docs-context.yml`.
- Generated docs are reproducible via `python3 scripts/generate_context_artifacts.py`.
- Scheduled stale-doc report exists in `.github/workflows/docs-garden.yml` (weekly cron).

## Follow-Up

- Remaining improvements tracked in `../tech-debt-tracker.md`.
