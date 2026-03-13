---
owner: sre
status: draft
last_verified: 2026-03-07
source_of_truth:
  - ../kb-server/app/workers/autosave.py
  - ../vault-sync/vault_sync/sync.py
related_code:
  - ../kb-server/app/services/git_batcher.py
  - ../kb-server/app/services/publish_service.py
related_tests:
  - ../kb-server/tests
  - ../vault-sync/tests/test_sync.py
review_cycle_days: 21
---

# Reliability

## Service Expectations

- `kb-server` readiness requires database and Git-backed vault access.
- `kb-server` retrieval endpoints should rebuild or refresh in-process graph state when visible note state changes.
- `mcp-server` should surface upstream `kb-server` failures as explicit tool errors rather than hanging or fabricating output.
- Autosave worker should tolerate transient Git/network failures.
- `vault-sync` should converge after temporary API outages.

## Failure Classes

- Dependency outage (DB, Git remote, GitHub API, webhook target)
- Local filesystem inconsistency
- Branch/PR drift from expected ownership model

## Reliability Signals

- API health and readiness checks.
- Retrieval endpoint latency/error rate and cache rebuild logs.
- Job/event tables for write and publish operations.
- Sync logs for pull/push loop success and retries.

## Operator Checks by Failure Class

### DB outage (`kb-server`)

- Signal: `GET /health` stays 200 while `GET /ready` returns non-200 with DB failure detail.
- Signal: API logs show database connection failures from readiness and write paths.
- Recovery check: when DB is restored, `GET /ready` returns 200 without process restart.

### Git remote / GitHub outage (`kb-server`)

- Signal: autosave or batcher logs show push/PR failures while local commits continue.
- Signal: pending API changes remain on `kb-api/*` branch until push/PR succeeds.
- Recovery check: retry loop or next batch cycle pushes and re-establishes PR state.

### API outage (`vault-sync`)

- Signal: sync loop logs pull/push request failures and keeps retrying on interval.
- Signal: local filesystem remains intact; no destructive cleanup on transient failures.
- Recovery check: after API is reachable, next pull repopulates `view=current` and pending local changes push successfully.

### API outage (`mcp-server`)

- Signal: MCP tools return upstream request failures with `kb-server` status/detail.
- Signal: note/resource reads fail closed rather than returning stale fabricated content.
- Recovery check: once `kb-server` is reachable, the next MCP tool invocation succeeds without restarting the adapter.

## Runbook Links

- `runbooks/deployment.md`
- `runbooks/incident-response.md`
- `runbooks/backup-restore.md`
