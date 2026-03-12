# KB Server

File-first knowledge base server. Watches a Markdown vault, auto-commits to Git, pushes to a remote, and triggers Quartz publishing.

## Prerequisites

- Python 3.10+
- Git 2.34+
- PostgreSQL 15+

## Quick start (development)

```bash
# Clone and enter the project
cd kb-server

# Create virtualenv and install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Copy and edit environment
cp .env.example .env
# Edit .env: set VAULT_PATH, DATABASE_URL, etc.

# Create the database
createdb kb

# Run migrations
alembic upgrade head

# Start the API
python -m uvicorn app.main:app --reload

# In another terminal, start the autosave worker
python -m app.workers.autosave
```

## Vault setup

The vault must be an existing Git repository:

```bash
mkdir -p /srv/flightdeck/vault
cd /srv/flightdeck/vault
git init
git remote add origin git@github.com:you/your-vault.git
```

Create the directory structure you want (these are conventions, not enforced):

```text
vault/
  notes/
  projects/
  people/
  daily/
  templates/
  assets/
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `VAULT_PATH` | `/srv/flightdeck/vault` | Absolute path to the vault Git repo |
| `DATABASE_URL` | `postgresql://kb:kb@localhost:5432/kb` | Postgres connection string |
| `KB_API_KEY` | (empty) | Deprecated fallback key used only when the `api_keys` table has no rows |
| `GIT_REMOTE` | `origin` | Git remote name |
| `GIT_BRANCH` | `main` | Base branch for PRs and autosave pushes |
| `GIT_PUSH_ENABLED` | `true` | Set `false` to commit without pushing |
| `AUTOSAVE_DEBOUNCE_SECONDS` | `30` | Seconds of quiet before autosave triggers |
| `GIT_PULL_INTERVAL_SECONDS` | `60` | How often to pull from remote (syncs merged PRs) |
| `GIT_BATCH_DEBOUNCE_SECONDS` | `10` | Seconds to debounce API-write batching |
| `GIT_BATCH_BRANCH_PREFIX` | `kb-api` | Prefix for daily feature branches (e.g., `kb-api/2026-03-05`) |
| `GITHUB_TOKEN` | (empty) | GitHub personal access token with `repo` scope for PR creation |
| `GITHUB_REPO` | (empty) | GitHub repository in `owner/repo` format |
| `QUARTZ_BUILD_COMMAND` | (empty) | Shell command to build Quartz site |
| `QUARTZ_WEBHOOK_URL` | (empty) | URL to POST after push to trigger rebuild |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API bind port |

> **Note:** Unknown env keys in `.env` are silently ignored, so extra variables won't break startup.
> **Note:** `GITHUB_TOKEN` is used for GitHub API PR calls, not for `git push/pull` auth.
> Git CLI operations run non-interactively and require preconfigured credentials (SSH key or PAT-backed credential helper).

## Process model

Two processes run side-by-side:

1. **kb-api** — FastAPI server handling note reads/writes and the publish endpoint.
2. **kb-worker** — File watcher that detects vault changes, debounces, commits, pushes, and triggers publishing.

Both share the vault filesystem and the Postgres database.

## Runtime supervision (current vs target)

Current standard in this repo is to run `kb-api` and `kb-worker` in a
dedicated `tmux` session.

For a copy-paste local `tmux` validation of role-based API keys plus
`vault-sync`, use `../docs/runbooks/local-role-auth-e2e.md`.

Example:

```bash
tmux new -s kb-runtime

# Pane/window 1
cd /path/to/flight-deck/kb-server
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Pane/window 2
cd /path/to/flight-deck/kb-server
source .venv/bin/activate
python -m app.workers.autosave
```

Planned next step is migrating this runtime to `systemctl`-managed services
for more durable process supervision.

## API endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Always 200 |
| `GET` | `/ready` | 200 when DB and vault are reachable |
| `GET` | `/notes/{path}` | Read a note |
| `PUT` | `/notes/{path}` | Write a note |
| `GET` | `/notes/?prefix=...` | List notes under a prefix |
| `POST` | `/publish` | Trigger a Quartz build manually |

## Using the API

Base URL (default): `http://localhost:8000`

FastAPI also exposes interactive docs:

- Swagger UI: `GET /docs`
- OpenAPI JSON: `GET /openapi.json`

### Authentication

`/health` and `/ready` are open. Every other route requires `X-API-Key`.

Preferred auth uses hashed API keys stored in the database. Create them with the
CLI after configuring `DATABASE_URL` and running migrations:

```bash
python -m app.cli.keys create --name "yash-laptop" --role user
python -m app.cli.keys create --name "claude-agent" --role agent
python -m app.cli.keys list
```

Roles map to server behavior:

- `readonly`: can read, cannot write or publish
- `user`: writes commit directly to `GIT_BRANCH`
- `agent`: writes batch to `kb-api/*` and create/update a PR
- `admin`: same write behavior as `user` today, reserved for future admin APIs

`KB_API_KEY` remains as a deprecated fallback. It is only used when the
`api_keys` table has no rows.

`/docs` and `/openapi.json` are protected like every other non-health route.

### Health and readiness

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

`/ready` reports errors until:

- Postgres is reachable via `DATABASE_URL`
- the vault directory exists at `VAULT_PATH`
- the vault is a Git repo (contains `VAULT_PATH/.git/`)

### Read a note

```bash
curl -H "X-API-Key: <api-key>" \
  http://localhost:8000/notes/notes/hello.md
```

Response shape:

```json
{
  "path": "notes/hello.md",
  "content": "# Hello\n...",
  "modified_at": "2026-03-04T00:00:00Z"
}
```

### Write a note

Use a `user`, `agent`, or `admin` key for writes. `readonly` keys receive `403`.

Agent-role writes stay review-gated through the PR workflow:

```bash
curl -X PUT http://localhost:8000/notes/notes/hello.md \
  -H "X-API-Key: <agent-key>" \
  -H "Content-Type: application/json" \
  -d '{"content":"# Hello\nCreated via API.\n"}'
```

API writes are batched in the background (configurable via
`GIT_BATCH_DEBOUNCE_SECONDS`). After the debounce window, the server:

1. Creates/checks out a daily feature branch (e.g., `kb-api/2026-03-05`)
2. Commits all batched changes (including deletions)
3. Pushes the branch to the remote
4. Creates or updates a PR targeting `GIT_BRANCH`

This ensures `agent` writes never push directly to main — they always go through a PR.

If you want an approved direct write, use a `user` or `admin` key instead.

Notes:

- Writes are limited to file extensions: `.md`, `.markdown`, `.txt`
- Paths must be relative to the vault (no absolute paths, no `..` traversal)

### List notes

List everything under a directory prefix:

```bash
curl -H "X-API-Key: <api-key>" \
  "http://localhost:8000/notes/?prefix=notes"
```

### Publish (Quartz trigger)

Manual publish trigger:

```bash
curl -X POST -H "X-API-Key: <write-capable-key>" http://localhost:8000/publish
```

If neither `QUARTZ_BUILD_COMMAND` nor `QUARTZ_WEBHOOK_URL` is set, `/publish` returns `501`.

### Common errors

- **401**: missing or invalid `X-API-Key` header
- **403**: authenticated key is read-only for the requested write/publish action
- **400**: path not allowed (bad extension, absolute path, traversal attempt)
- **404**: note not found
- **500**: Git failure (e.g., repo misconfigured) or DB issues

### Path encoding gotcha

If you have spaces or special characters in filenames, URL-encode them.
Example:

```bash
curl "http://localhost:8000/notes/notes/My%20Note.md"
```

## Service deployment (planned systemd migration)

Install the project:

```bash
sudo mkdir -p /opt/kb-server
sudo cp -r . /opt/kb-server/
cd /opt/kb-server
python -m venv .venv
source .venv/bin/activate
pip install .
cp .env.example .env
# Edit .env for production values
```

Install and enable the services:

```bash
sudo cp scripts/kb-api.service /etc/systemd/system/
sudo cp scripts/kb-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kb-api kb-worker
```

Check status:

```bash
sudo systemctl status kb-api kb-worker
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"
```

## Backup and restore

**Vault:** The vault is a Git repo. The remote (GitHub/Gitea) is the backup. You can also snapshot the directory.

**Database:** Standard `pg_dump` / `pg_restore`:

```bash
pg_dump -Fc kb > kb-backup.dump
pg_restore -d kb kb-backup.dump
```

The database is metadata only. If lost, you lose job history and event logs, but the vault content is unaffected.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `/ready` reports `db` error | Verify `DATABASE_URL` and that Postgres is running |
| `/ready` reports vault missing | Verify `VAULT_PATH` points to a git-initialized directory |
| Autosave not triggering | Check worker logs; verify `AUTOSAVE_DEBOUNCE_SECONDS` isn't too high |
| Push failing | Verify git remote/auth is preconfigured for non-interactive use (SSH key or PAT credential helper); GitHub password auth is not supported |
| Publish not running | Verify `QUARTZ_BUILD_COMMAND` or `QUARTZ_WEBHOOK_URL` is set |

## Running tests

```bash
pip install -e ".[dev]"
pytest -v
```

Tests use temporary directories and SQLite in-memory — no Postgres or vault required.
