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
- With auth enabled, non-admin HTTP routes require `X-API-Key`, including `/health`, `/ready`, `/docs`, and `/openapi.json`.
- `/admin` and `/admin/api/*` are intentionally exempt from `X-API-Key` so the local operator dashboard can bootstrap and operate the instance.
- With auth disabled (`KB_API_KEY` empty), requests are accepted without API-key checks.
- `KB_API_KEY` must never be committed in docs examples with live values.

## Secret Handling

- Preferred model: secrets such as `KB_API_KEY` and `GITHUB_TOKEN` live in deployment secret stores or process environment variables.
- Supported local/dev model: `/admin` can write `KB_API_KEY` and `GITHUB_TOKEN` into local `.env`.
- Admin responses must not echo stored secret values back to the browser after save.
- Docs should only reference secret names, not values.
- Generated docs must redact secrets by default.

## Write Safety

- Path traversal and absolute-path writes are denied.
- Only approved file types are writable.
- Writes from `source=api` remain review-gated through PR workflow.
- Admin config writes change local instance configuration only; they do not authorize content writes outside existing approval boundaries.
- Admin start/restart actions only launch the configured local shell commands; they do not elevate privileges or infer a process manager.

## Security Review Triggers

Update this document when changing:

- auth middleware/dependency behavior
- admin route exposure or operator trust boundary
- request validation and path sanitization
- secret storage or secret presentation behavior in admin/config flows
- external webhook/publish execution semantics
- GitHub token scope or PR automation behavior
