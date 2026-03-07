---
owner: product
status: draft
last_verified: 2026-03-07
source_of_truth:
  - product-specs/index.md
related_code:
  - ../kb-server/app/api/routes/notes.py
  - ../vault-sync/vault_sync/sync.py
related_tests:
  - ../kb-server/tests
  - ../vault-sync/tests
review_cycle_days: 30
---

# Product Sense

## User Promise

- Humans get fast local editing and explicit approval control.
- Agents can propose broad changes without bypassing review.
- Everyone can inspect latest visible state via `current`.

## Product Tradeoffs

- Reviewability over raw write throughput for agent-origin changes.
- Explicit semantics (`view`, `source`) over ambiguous branch behavior.
- Operational simplicity prioritized for small-team ownership.

## Decision Filters

When evaluating changes:

- does this preserve approval boundaries?
- does this improve or degrade human editing ergonomics?
- is the behavior observable and testable?
- does docs/automation cost stay proportional to complexity?

