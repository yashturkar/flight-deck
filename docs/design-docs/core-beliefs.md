---
owner: architecture
status: verified
last_verified: 2026-03-14
source_of_truth:
  - ../../AGENTS.md
  - ../../kb-server/BRANCHING_AND_CURRENT_VIEW.md
related_code:
  - ../../kb-server/app/api/routes/notes.py
  - ../../kb-server/app/services/current_view_service.py
related_tests:
  - ../../kb-server/tests/test_current_view.py
review_cycle_days: 30
---

# Core Beliefs

## Agent-First Context Design

- Start with a map, not a monolith.
- Prefer progressive disclosure over all-at-once guidance.
- Treat docs as navigational and operational assets, not prose dumps.
- Prefer explicit, observable workflows over ambiguous convenience.

## System Invariants

- `main` is approved truth.
- `kb-api/*` is pending and review-bound.
- `current` is composed read state with provenance.
- Human intent and agent intent remain separable in workflows.
- Reviewability matters more than raw write throughput for agent-origin changes.
- Human editing ergonomics must stay simple even when approval boundaries exist.

## Documentation Beliefs

- Durable docs live in `docs/`.
- Root `AGENTS.md` remains short and index-like.
- Every durable doc declares owner, freshness, and source links.
- CI should catch drift before it becomes institutional memory debt.
- Thin meta-docs should be merged away when they stop carrying unique guidance.

## Execution Beliefs

- Plans are first-class and versioned.
- Small changes may use lightweight plans; complex work uses execution plans.
- Decision logs should stay with plans until completion.
