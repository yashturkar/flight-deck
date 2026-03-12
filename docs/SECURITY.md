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

- `/health` and `/ready` are always open for probes.
- All other HTTP routes require `X-API-Key`.
- Preferred auth uses hashed API keys stored in the `api_keys` table.
- `KB_API_KEY` is a deprecated fallback that only applies when the `api_keys` table has no rows.
- Caller identity is derived from the authenticated key role:
  - `readonly`: read-only access
  - `user`: direct approved writes
  - `agent`: PR-gated writes
  - `admin`: direct approved writes plus future admin-only actions
- `KB_API_KEY` must never be committed in docs examples with live values.

## Secret Handling

- Secrets remain in local `.env` files or deployment secret stores.
- Docs should only reference secret names, not values.
- Generated docs must redact secrets by default.
- When dual Git identities are configured, keep USER and AGENT SSH commands/keys and `GITHUB_AGENT_TOKEN` in secret storage only.

## Write Safety

- Path traversal and absolute-path writes are denied.
- Only approved file types are writable.
- `agent`-role writes remain review-gated through PR workflow.
- `user` and `admin` writes commit directly to the configured base branch.
- `readonly` keys receive `403` on write or publish endpoints.
- Git subprocesses must use per-command identity env (`GIT_AUTHOR_*`, `GIT_COMMITTER_*`, `GIT_SSH_COMMAND`) instead of mutating shared repo config at runtime.

## Security Review Triggers

Update this document when changing:

- auth middleware/dependency behavior
- request validation and path sanitization
- external webhook/publish execution semantics
- GitHub token scope or PR automation behavior
