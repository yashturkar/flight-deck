---
owner: sre
status: draft
last_verified: 2026-03-07
source_of_truth:
  - ../../kb-server/app/workers/autosave.py
  - ../../kb-server/app/services/git_service.py
related_code:
  - ../../vault-sync/vault_sync/sync.py
related_tests:
  - ../../kb-server/tests
review_cycle_days: 14
---

# Incident Response Runbook

## Triage Checklist

- Identify blast radius: API-only, worker-only, sync client-only, or full system.
- Confirm dependency status: DB, Git remote, GitHub API, network.
- Inspect recent commits/PRs affecting write or view semantics.

## Common Incidents

- API write queue stuck.
- Autosave push failures.
- `current` view inconsistency.
- Sync loop churn or failed convergence.

## Immediate Actions

- Pause non-essential automations if data safety is at risk.
- Capture logs and relevant branch/PR state.
- Restore service to known-safe behavior before feature fixes.

