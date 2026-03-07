---
owner: security
status: draft
last_verified: 2026-03-07
source_of_truth:
  - ../kb-server/app/core/auth.py
  - ../kb-server/app/core/config.py
related_code:
  - ../kb-server/app/main.py
  - ../vault-sync/vault_sync/api_client.py
related_tests:
  - ../kb-server/tests
review_cycle_days: 21
---

# Security

## Auth Boundary

- API key auth is enforced by server middleware/dependencies when configured.
- `KB_API_KEY` must never be committed in docs examples with live values.

## Secret Handling

- Secrets remain in local `.env` files or deployment secret stores.
- Docs should only reference secret names, not values.
- Generated docs must redact secrets by default.

## Write Safety

- Path traversal and absolute-path writes are denied.
- Only approved file types are writable.
- Writes from `source=api` remain review-gated through PR workflow.

## Security Review Triggers

Update this document when changing:

- auth middleware/dependency behavior
- request validation and path sanitization
- external webhook/publish execution semantics
- GitHub token scope or PR automation behavior

