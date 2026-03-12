---
owner: platform
status: draft
last_verified: 2026-03-07
source_of_truth:
  - ../../kb-server/README.md
  - ../../vault-sync/README.md
  - ../../kb-server/app/api/routes/notes.py
  - ../../vault-sync/vault_sync/sync.py
related_code:
  - ../../kb-server/app/workers/autosave.py
  - ../../kb-server/app/services/git_batcher.py
  - ../../vault-sync/vault_sync/watcher.py
related_tests:
  - ../../kb-server/tests/test_current_view.py
  - ../../kb-server/tests/test_source_and_delete.py
  - ../../vault-sync/tests/test_sync.py
review_cycle_days: 14
---

# Autonomous Agent End-to-End Workflow

Use this runbook when an agent needs to autonomously build, review, test, and
fix features across `kb-server` and `vault-sync`.

## Primary goal

Validate real workflow behavior end-to-end, not only unit tests:

- server + worker running
- sync daemon running
- test vault exercising read/write/delete paths
- push/pull/current-view semantics verified
- regressions fixed before final report

## Required runtime model

For now, run services in `tmux` (this is the standard runtime in this repo).
Systemd migration is planned later.

## Environment bootstrap

Create disposable paths (examples):

- test vault: `/tmp/flightdeck-test-vault`
- sync dir: `/tmp/flightdeck-sync`
- test db: `kb_test` (or isolated URL)

Set `.env` values in `kb-server/.env` and `vault-sync/.env` to point to these
test resources.

## Bring up stack in tmux

```bash
# kb-server terminal
cd /path/to/flight-deck/kb-server
source .venv/bin/activate
alembic upgrade head

tmux new -s fd-e2e
# pane 1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# pane 2
python -m app.workers.autosave
```

```bash
# vault-sync terminal
cd /path/to/flight-deck/vault-sync
source .venv/bin/activate
vault-sync --server http://localhost:8000 --dir /tmp/flightdeck-sync --interval 10 --debounce 1 -v
```

## Autonomous test matrix

Agent should execute and validate all of the following:

1. **Agent-key API write path**
   - write/update/delete note through API
   - confirm batching branch + PR workflow behavior
2. **User-key human write path**
   - update and delete via sync dir edits
   - confirm direct commit/push behavior
3. **Current view behavior**
   - verify reads with `view=main` vs `view=current`
   - verify `view=current` rejects writes
4. **Bidirectional sync**
   - edit from API side, verify sync pull
   - edit from local sync side, verify server update
5. **Conflict/edge behavior**
   - rapid edits, delete/recreate, unusual filenames, and debounce timing
6. **Outage recovery behavior**
   - stop DB temporarily and verify `/ready` fails, then recovers after DB restore
   - simulate temporary API outage during sync and verify retry + convergence
   - simulate remote push/PR failure and verify pending changes recover on retry

## Acceptance criteria

- All impacted unit tests pass.
- E2E matrix above is completed with evidence.
- Any discovered bug is fixed and retested in the same run.
- Docs for changed behavior are updated in the same branch.
- Failure-mode runs include observed signals/log lines and explicit recovery proof.

## Agent execution loop

1. implement feature or fix
2. run unit tests
3. run this E2E runbook
4. capture failures with reproduction notes
5. patch code/docs
6. rerun tests + E2E
7. summarize outcomes and residual risks

## Output format (what agent should report)

- setup used (`tmux` session names, test paths, env assumptions)
- test matrix pass/fail table
- bugs found and fixes applied
- files changed
- remaining risks and follow-up tasks

## Expected Reliability Signals During E2E

- DB outage: `/health` remains 200; `/ready` reports DB failure until restore.
- API outage for sync: sync loop logs request failures, then recovers on next interval.
- Git/PR outage: autosave or batch logs push/PR failures without dropping local changes.
