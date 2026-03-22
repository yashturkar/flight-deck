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
- `/admin` should surface the same readiness blockers and recent operational signals visible through logs and DB-backed job/event tables.
- The Streamlit dashboard should degrade cleanly when the FastAPI backend is offline and still allow operators to launch configured start commands.
- Autosave worker should tolerate transient Git/network failures.
- `vault-sync` should converge after temporary API outages.

## Failure Classes

- Dependency outage (DB, Git remote, GitHub API, webhook target)
- Local filesystem inconsistency
- Branch/PR drift from expected ownership model

## Reliability Signals

- API health and readiness checks.
- Admin dashboard state for config source, readiness blockers, git state, pending batch paths, and PR visibility.
- Job/event tables for write and publish operations.
- Sync logs for pull/push loop success and retries.

## Operator Checks by Failure Class

### DB outage (`kb-server`)

- Signal: `GET /health` stays 200 while `GET /ready` returns non-200 with DB failure detail.
- Signal: `/admin` shows DB not ready and surfaces the same readiness error.
- Signal: API logs show database connection failures from readiness and write paths.
- Recovery check: when DB is restored, `GET /ready` returns 200 without process restart.

### Git remote / GitHub outage (`kb-server`)

- Signal: autosave or batcher logs show push/PR failures while local commits continue.
- Signal: `/admin` PR summary shows GitHub/API errors or empty PR visibility despite queued/pushed work.
- Signal: pending API changes remain on `kb-api/*` branch until push/PR succeeds.
- Recovery check: retry loop or next batch cycle pushes and re-establishes PR state.

### Config drift / restart-needed state (`kb-server`)

- Signal: `/admin` shows updated `.env` values, but runtime behavior still reflects old DB/auth/process settings.
- Cause: some settings are effectively startup-bound because the API process and worker initialize long-lived config or connections at startup.
- Recovery check: restart `kb-api` and `kb-worker`, then confirm `/admin` and `/ready` reflect the expected state.

### API offline but local dashboard available (`kb-server`)

- Signal: Streamlit dashboard reports backend offline instead of crashing.
- Cause: `kb-api` is down, misbound, or unreachable at the configured backend URL.
- Recovery check: launch the derived tmux start command via the dashboard, rerun the dashboard, and confirm `/admin/api/state` responds again.

### Autosave worker offline (`kb-server`)

- Signal: Streamlit dashboard shows worker runtime config but autosave activity stops advancing.
- Cause: `kb-worker` tmux session is down or was never started.
- Recovery check: launch or restart the worker from the dashboard and confirm vault events resume.

### API outage (`vault-sync`)

- Signal: sync loop logs pull/push request failures and keeps retrying on interval.
- Signal: local filesystem remains intact; no destructive cleanup on transient failures.
- Recovery check: after API is reachable, next pull repopulates `view=current` and pending local changes push successfully.

## Runbook Links

- `runbooks/deployment.md`
- `runbooks/incident-response.md`
- `runbooks/backup-restore.md`
