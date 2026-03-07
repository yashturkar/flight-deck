---
owner: client
status: verified
last_verified: 2026-03-07
source_of_truth:
  - ../../vault-sync/vault_sync/sync.py
  - ../../vault-sync/vault_sync/config.py
  - ../../vault-sync/vault_sync/cli.py
related_code:
  - ../../vault-sync/vault_sync/api_client.py
  - ../../vault-sync/vault_sync/watcher.py
related_tests:
  - ../../vault-sync/tests/test_sync.py
review_cycle_days: 14
---

# Product Spec: vault-sync

## Purpose

Provide a local filesystem editing experience while syncing with kb-server's `current` view.

## User-Visible Behavior

- On startup, daemon pulls full `view=current` into `SYNC_DIR`.
- Local edits and deletes are observed and pushed as `source=human`.
- Daemon periodically repulls to absorb remote updates and pending content.
- Supported local file extensions match server constraints.

## Convergence Rules

- Pull is source of truth for complete visible state.
- Push sends only changed/deleted local files.
- Echo suppression prevents immediate re-processing of pull-written files.

## Operator Controls

- `SYNC_PULL_INTERVAL_SECONDS` controls refresh cadence.
- `SYNC_DEBOUNCE_SECONDS` controls write burst handling.
- `KB_SERVER_URL` and `KB_API_KEY` define server auth target.

## Related Docs

- `../../vault-sync/README.md`
- `../CLIENTS.md`
- `../RELIABILITY.md`

