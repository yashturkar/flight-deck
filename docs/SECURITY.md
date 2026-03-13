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

- API key auth is enforced by server middleware when configured (`KB_API_KEY` non-empty).
- With auth enabled, all HTTP routes require `X-API-Key`, including `/health`, `/ready`, `/docs`, and `/openapi.json`.
- With auth disabled (`KB_API_KEY` empty), requests are accepted without API-key checks.
- `KB_API_KEY` must never be committed in docs examples with live values.

## Secret Handling

- Secrets remain in local `.env` files or deployment secret stores.
- Docs should only reference secret names, not values.
- Generated docs must redact secrets by default.
- `mcp-server` stores `KB_API_KEY` locally and must never echo it back through tool output or logs.

## MCP Boundary

- `mcp-server` is a local adapter over `kb-server`, not a second source of truth.
- v1 transport is stdio only; no remote MCP transport is exposed by default.
- MCP writes must use `source=api` and must not expose a path to `source=human`.

## Write Safety

- Path traversal and absolute-path writes are denied.
- Only approved file types are writable.
- Writes from `source=api` remain review-gated through PR workflow.

## Security Review Triggers

Update this document when changing:

- auth middleware/dependency behavior
- request validation and path sanitization
- MCP transport or upstream auth handling
- external webhook/publish execution semantics
- GitHub token scope or PR automation behavior
