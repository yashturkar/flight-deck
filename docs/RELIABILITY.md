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
- Autosave worker should tolerate transient Git/network failures.
- `vault-sync` should converge after temporary API outages.

## Failure Classes

- Dependency outage (DB, Git remote, GitHub API, webhook target)
- Local filesystem inconsistency
- Branch/PR drift from expected ownership model

## Reliability Signals

- API health and readiness checks.
- Job/event tables for write and publish operations.
- Sync logs for pull/push loop success and retries.

## Runbook Links

- `runbooks/deployment.md`
- `runbooks/incident-response.md`
- `runbooks/backup-restore.md`

