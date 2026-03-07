---
owner: sre
status: draft
last_verified: 2026-03-07
source_of_truth:
  - ../../kb-server/README.md
  - ../../vault-sync/README.md
  - ../../kb-server/scripts/kb-api.service
  - ../../kb-server/scripts/kb-worker.service
related_code:
  - ../../kb-server/scripts/setup_linux.sh
  - ../../vault-sync/vault_sync/sync.py
related_tests:
  - ../../kb-server/tests
review_cycle_days: 21
---

# Deployment Runbook

## Runtime strategy

- **Current state:** run `kb-server` processes inside a dedicated `tmux` session.
- **Target state:** migrate to `systemctl` services once service wrappers and ops checks are finalized.

## kb-server

- Install Python environment and package.
- Configure `.env` with vault/db/auth settings.
- Apply DB migrations.

### Current runtime (tmux)

```bash
tmux new -s kb-runtime

# Window/pane: API
cd /path/to/flight-deck/kb-server
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Window/pane: worker
cd /path/to/flight-deck/kb-server
source .venv/bin/activate
python -m app.workers.autosave
```

### Planned runtime (systemd)

Deploy `kb-api` and `kb-worker` systemd units after migration:

```bash
cd /path/to/flight-deck/kb-server
sudo cp scripts/kb-api.service /etc/systemd/system/
sudo cp scripts/kb-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kb-api kb-worker
```

## vault-sync

- Install package in virtualenv.
- Configure daemon `.env`.
- Current default: run from terminal/tmux.
- Optional: run as user service when needed.

## Post-Deploy Validation

- `GET /health` and `GET /ready`.
- verify push/pull behavior with one test note.
- verify `view=current` returns composed content.
- run `docs/runbooks/autonomous-agent-e2e.md` for full end-to-end validation.

