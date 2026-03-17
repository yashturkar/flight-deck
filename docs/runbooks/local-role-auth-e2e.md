---
owner: platform
status: draft
last_verified: 2026-03-14
source_of_truth:
  - ../../kb-server/README.md
  - ../../kb-server/app/core/auth.py
  - ../../kb-server/app/api/routes/notes.py
  - ../../vault-sync/vault_sync/api_client.py
related_code:
  - ../../kb-server/app/cli/keys.py
  - ../../kb-server/app/services/git_batcher.py
  - ../../vault-sync/vault_sync/sync.py
related_tests:
  - ../../kb-server/tests/test_auth.py
  - ../../kb-server/tests/test_notes_api.py
  - ../../vault-sync/tests/test_api_client.py
  - ../../vault-sync/tests/test_sync.py
review_cycle_days: 14
---

# Local Role-Auth E2E

Use this runbook to validate the role-based API key flow locally with `tmux`,
an isolated vault, and a sample `vault-sync` client.

## Goal

Verify all three behaviors together:

- `readonly` keys can read but cannot write
- `agent` keys write to `kb-api/*` and show up in `view=current`
- `user` keys write directly to `main`, including through `vault-sync`

## Prerequisites

- repo-local virtualenvs already created:
  - `kb-server/.venv`
  - `vault-sync/.venv`
- `tmux` installed
- `git` available

This runbook uses repo-local interpreters:

- `kb-server/.venv/bin/python`
- `vault-sync/.venv/bin/python`

## Create isolated test resources

```bash
tmpdir=$(mktemp -d /tmp/fd-auth-e2e.XXXXXX)
mkdir -p "$tmpdir/vault" "$tmpdir/sync"

git init --bare "$tmpdir/remote.git"
git init -b main "$tmpdir/vault"
git -C "$tmpdir/vault" config user.email e2e@test.local
git -C "$tmpdir/vault" config user.name e2e-test

mkdir -p "$tmpdir/vault/notes"
printf '# Seed\n' > "$tmpdir/vault/notes/seed.md"
git -C "$tmpdir/vault" add .
git -C "$tmpdir/vault" commit -m "seed"
git -C "$tmpdir/vault" remote add origin "$tmpdir/remote.git"
git -C "$tmpdir/vault" push -u origin main
```

Create env files for the isolated run:

```bash
cat > "$tmpdir/kb-server.env" <<EOF
VAULT_PATH=$tmpdir/vault
DATABASE_URL=sqlite:///$tmpdir/kb-server.db
KB_API_KEY=
GIT_REMOTE=origin
GIT_BRANCH=main
GIT_PUSH_ENABLED=false
GIT_USER_AUTHOR_NAME=sync-user
GIT_USER_AUTHOR_EMAIL=sync-user@test.local
GIT_USER_COMMITTER_NAME=sync-user
GIT_USER_COMMITTER_EMAIL=sync-user@test.local
GIT_USER_SSH_COMMAND=
GIT_AGENT_AUTHOR_NAME=agent-bot
GIT_AGENT_AUTHOR_EMAIL=agent-bot@test.local
GIT_AGENT_COMMITTER_NAME=agent-bot
GIT_AGENT_COMMITTER_EMAIL=agent-bot@test.local
GIT_AGENT_SSH_COMMAND=
GIT_AGENT_HTTPS_TOKEN=
GIT_BATCH_DEBOUNCE_SECONDS=2
GIT_BATCH_BRANCH_PREFIX=kb-api
GITHUB_TOKEN=
GITHUB_AGENT_TOKEN=
GITHUB_REPO=
AUTOSAVE_DEBOUNCE_SECONDS=2
GIT_PULL_INTERVAL_SECONDS=30
QUARTZ_BUILD_COMMAND=
QUARTZ_WEBHOOK_URL=
API_HOST=127.0.0.1
API_PORT=8011
EOF

cat > "$tmpdir/vault-sync.env" <<EOF
KB_SERVER_URL=http://127.0.0.1:8011
KB_API_KEY=
SYNC_DIR=$tmpdir/sync
SYNC_DEBOUNCE_SECONDS=1
SYNC_PULL_INTERVAL_SECONDS=4
EOF
```

## Prepare the database and API keys

```bash
cd /path/to/flight-deck/kb-server
set -a
source "$tmpdir/kb-server.env"
set +a

./.venv/bin/alembic upgrade head

./.venv/bin/python -m app.cli.keys create --name "sync-user" --role user
./.venv/bin/python -m app.cli.keys create --name "agent-bot" --role agent
./.venv/bin/python -m app.cli.keys create --name "viewer" --role readonly
./.venv/bin/python -m app.cli.keys list
```

Copy the printed plaintext keys. Put the `user` key into the `vault-sync` env:

```bash
sed -i '' 's|^KB_API_KEY=.*|KB_API_KEY=<user-key>|' "$tmpdir/vault-sync.env"
```

## Start the stack in tmux

```bash
tmux new-session -d -s fd-auth-e2e \
  'cd /path/to/flight-deck/kb-server && set -a && source '"$tmpdir"'/kb-server.env && set +a && ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8011'

tmux split-window -h -t fd-auth-e2e \
  'cd /path/to/flight-deck/vault-sync && set -a && source '"$tmpdir"'/vault-sync.env && set +a && ./.venv/bin/python -m vault_sync.cli -v'

tmux attach -t fd-auth-e2e
```

If you do not want to attach immediately, inspect panes later with:

```bash
tmux capture-pane -pt fd-auth-e2e:0.0
tmux capture-pane -pt fd-auth-e2e:0.1
```

## Validate server behavior

Health should be open:

```bash
curl http://127.0.0.1:8011/health
```

`readonly` key checks:

```bash
curl -H "X-API-Key: <readonly-key>" \
  http://127.0.0.1:8011/notes/notes/seed.md

curl -X PUT \
  -H "X-API-Key: <readonly-key>" \
  -H "Content-Type: application/json" \
  -d '{"content":"blocked\n"}' \
  http://127.0.0.1:8011/notes/notes/blocked.md

curl -X POST \
  -H "X-API-Key: <readonly-key>" \
  http://127.0.0.1:8011/publish
```

Expected:

- read returns `200`
- write returns `403`
- publish returns `403`

`agent` key checks:

```bash
curl -X PUT \
  -H "X-API-Key: <agent-key>" \
  -H "Content-Type: application/json" \
  -d '{"content":"# Agent\nPending branch write\n"}' \
  http://127.0.0.1:8011/notes/notes/agent-e2e.md

sleep 4

curl -H "X-API-Key: <agent-key>" \
  "http://127.0.0.1:8011/notes/notes/agent-e2e.md?view=main"

curl -H "X-API-Key: <agent-key>" \
  "http://127.0.0.1:8011/notes/notes/agent-e2e.md?view=current"
```

Expected:

- write returns `200`
- `view=main` returns `404`
- `view=current` returns `200`

Confirm the batch branch exists:

```bash
branch="kb-api/$(date -u +%F)"
git -C "$tmpdir/vault" branch --list "$branch"
git -C "$tmpdir/vault" log "$branch" -1 --format='%s'
git -C "$tmpdir/vault" ls-remote --heads origin
```

Expected:

- local branch exists
- latest branch commit resembles `kb-api: update notes/agent-e2e.md`
- the branch is present on `origin`

## Validate `vault-sync` user flow

Wait for the initial sync pull, then confirm the sync dir contains:

- `notes/seed.md`
- `notes/agent-e2e.md`

Create a local file through the synced surface:

```bash
printf '# From Sync\nclient write\n' > "$tmpdir/sync/notes/from-sync.md"
sleep 3
```

Confirm the write landed on `main`:

```bash
git -C "$tmpdir/vault" log main -1 --format='%s'
git -C "$tmpdir/vault" show main:notes/from-sync.md
```

Expected:

- latest main commit resembles `sync-user: update notes/from-sync.md`
- file content matches the local sync edit

## Shutdown

```bash
tmux kill-session -t fd-auth-e2e
rm -rf "$tmpdir"
```

## Acceptance criteria

- `readonly` read succeeds and write-capable routes return `403`
- `agent` writes land on `kb-api/*` and appear in `view=current`, not `view=main`
- `vault-sync` pulls `current` and a local edit commits directly to `main`
- tmux panes show the expected API requests and commit activity

## Reliability signals

- `/health` stays reachable throughout the run
- `vault-sync` continues polling `view=current` after the local push
- agent batching either pushes the branch successfully or logs a PR-creation failure without dropping the branch commit

## Expected outcomes summary

- `readonly` is enforced at `403` for write-capable routes
- `agent` writes stay off `main` and appear in `current`
- `vault-sync` uses the authenticated key role and no longer sends `source=*`
