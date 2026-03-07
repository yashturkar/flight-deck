---
owner: client
status: draft
last_verified: 2026-03-07
source_of_truth:
  - product-specs/vault-sync.md
related_code:
  - ../vault-sync/vault_sync/cli.py
  - ../vault-sync/vault_sync/sync.py
related_tests:
  - ../vault-sync/tests/test_sync.py
review_cycle_days: 21
---

# Clients

## Supported Client

- `vault-sync`: local daemon for pull/current and human-source push.

## Client Contract

- Pull from `view=current`.
- Push edits/deletes as `source=human`.
- Preserve path and extension constraints enforced by server.

## Planned Future Clients

- Optional editor plugins should reuse the same view/source semantics.
- Any new client must link to test coverage and failure-mode runbooks.

