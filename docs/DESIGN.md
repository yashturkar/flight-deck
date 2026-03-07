---
owner: architecture
status: draft
last_verified: 2026-03-07
source_of_truth:
  - design-docs/index.md
related_code:
  - ../kb-server/app/services/current_view_service.py
  - ../vault-sync/vault_sync/sync.py
related_tests:
  - ../kb-server/tests/test_current_view.py
  - ../vault-sync/tests/test_sync.py
review_cycle_days: 30
---

# Design

## Design Principles

- Preserve separation of approved vs pending content.
- Keep human editing ergonomics while retaining reviewability for agent output.
- Prefer additive, observable workflows over implicit magic.

## Cross-Domain Patterns

- Compose views at read time where possible.
- Keep ownership boundaries explicit in API semantics.
- Use generated docs and tests to reduce narrative drift.

## References

- `design-docs/core-beliefs.md`
- `product-specs/kb-server.md`
- `product-specs/vault-sync.md`

