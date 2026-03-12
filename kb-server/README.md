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
| `KB_API_KEY` | (empty) | API key required in every request (`X-API-Key` header). Leave blank to disable auth (dev only) |
| `GIT_REMOTE` | `origin` | Git remote name |
| `GIT_BRANCH` | `main` | Base branch for PRs and autosave pushes |
| `GIT_PUSH_ENABLED` | `true` | Set `false` to commit without pushing |
| `AUTOSAVE_DEBOUNCE_SECONDS` | `30` | Seconds of quiet before autosave triggers |
| `GIT_PULL_INTERVAL_SECONDS` | `60` | How often to pull from remote (syncs merged PRs) |
| `GIT_BATCH_DEBOUNCE_SECONDS` | `10` | Seconds to debounce API-write batching |
| `GIT_BATCH_BRANCH_PREFIX` | `kb-api` | Prefix for daily feature branches (e.g., `kb-api/2026-03-05`) |
| `GIT_USER_AUTHOR_NAME` | (empty) | Git author name for `source=human` writes and autosave commits |
| `GIT_USER_AUTHOR_EMAIL` | (empty) | Git author email for `source=human` writes and autosave commits |
| `GIT_USER_COMMITTER_NAME` | (empty) | Optional Git committer name for human-origin writes (defaults to author name) |
| `GIT_USER_COMMITTER_EMAIL` | (empty) | Optional Git committer email for human-origin writes (defaults to author email) |
| `GIT_USER_SSH_COMMAND` | (empty) | Optional SSH command for human-origin `git push/pull` (for example a USER SSH key) |
| `GIT_AGENT_AUTHOR_NAME` | (empty) | Git author name for `source=api` batch commits |
| `GIT_AGENT_AUTHOR_EMAIL` | (empty) | Git author email for `source=api` batch commits |
| `GIT_AGENT_COMMITTER_NAME` | (empty) | Optional Git committer name for API-origin writes (defaults to author name) |
| `GIT_AGENT_COMMITTER_EMAIL` | (empty) | Optional Git committer email for API-origin writes (defaults to author email) |
| `GIT_AGENT_SSH_COMMAND` | (empty) | Optional SSH command for API-origin branch pushes (for example an AGENT SSH key) |
| `GITHUB_TOKEN` | (empty) | Legacy fallback GitHub personal access token for PR creation |
| `GITHUB_AGENT_TOKEN` | (empty) | Preferred GitHub personal access token with `repo` scope for AGENT PR creation/update |
| `GITHUB_REPO` | (empty) | GitHub repository in `owner/repo` format |
| `QUARTZ_BUILD_COMMAND` | (empty) | Shell command to build Quartz site |
| `QUARTZ_WEBHOOK_URL` | (empty) | URL to POST after push to trigger rebuild |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API bind port |

> **Note:** Unknown env keys in `.env` are silently ignored, so extra variables won't break startup.
> **Note:** `GITHUB_AGENT_TOKEN` is preferred for AGENT PR calls; `GITHUB_TOKEN` remains a fallback for backward compatibility.
> Git CLI operations run non-interactively and require preconfigured credentials (SSH key or PAT-backed credential helper). USER and AGENT credentials are injected per command rather than written into shared git config.

## Process model

Two processes run side-by-side:

1. **kb-api** — FastAPI server handling note reads/writes and the publish endpoint.
2. **kb-worker** — File watcher that detects vault changes, debounces, commits, pushes, and triggers publishing.

Both share the vault filesystem and the Postgres database.

## Runtime supervision (current vs target)

Current standard in this repo is to run `kb-api` and `kb-worker` in a
dedicated `tmux` session.

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

When `KB_API_KEY` is set, **every** request (including `/health`, `/ready`,
`/docs`, and `/openapi.json`) must include the key:

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/health
```

Requests without a valid key receive a `401` response.

When `KB_API_KEY` is left blank (development mode), no authentication is
required.

### Health and readiness

```bash
curl -H "X-API-Key: $KB_API_KEY" http://localhost:8000/health
curl -H "X-API-Key: $KB_API_KEY" http://localhost:8000/ready
```

`/ready` reports errors until:

- Postgres is reachable via `DATABASE_URL`
- the vault directory exists at `VAULT_PATH`
- the vault is a Git repo (contains `VAULT_PATH/.git/`)

### Read a note

```bash
curl -H "X-API-Key: $KB_API_KEY" \
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

```bash
curl -X PUT http://localhost:8000/notes/notes/hello.md \
  -H "X-API-Key: $KB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content":"# Hello\nCreated via API.\n"}'
```

API writes are batched in the background (configurable via
`GIT_BATCH_DEBOUNCE_SECONDS`). After the debounce window, the server:

1. Creates/checks out a daily feature branch (e.g., `kb-api/2026-03-05`)
2. Commits all batched changes (including deletions)
3. Pushes the branch to the remote
4. Creates or updates a PR targeting `GIT_BRANCH`

This ensures API writes never push directly to main — they always go through a PR.

By default, `PUT /notes/...` uses `source=api`. To route writes explicitly:

```bash
# Human-origin write: commit/push directly to GIT_BRANCH as USER
curl -X PUT "http://localhost:8000/notes/notes/human.md?source=human" \
  -H "X-API-Key: $KB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content":"# Human change\n"}'

# API-origin write: batch to kb-api/* branch and PR as AGENT
curl -X PUT "http://localhost:8000/notes/notes/agent.md?source=api" \
  -H "X-API-Key: $KB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content":"# Agent change\n"}'
```

Identity routing rules:

- `source=human` → commit as USER and push as USER
- `source=api` → commit as AGENT, push as AGENT, and create/update PR as AGENT

Notes:

- Writes are limited to file extensions: `.md`, `.markdown`, `.txt`
- Paths must be relative to the vault (no absolute paths, no `..` traversal)

### List notes

List everything under a directory prefix:

```bash
curl -H "X-API-Key: $KB_API_KEY" \
  "http://localhost:8000/notes/?prefix=notes"
```

### Publish (Quartz trigger)

Manual publish trigger:

```bash
curl -X POST -H "X-API-Key: $KB_API_KEY" http://localhost:8000/publish
```

If neither `QUARTZ_BUILD_COMMAND` nor `QUARTZ_WEBHOOK_URL` is set, `/publish` returns `501`.

### Common errors

- **401**: missing or invalid `X-API-Key` header (or `KB_API_KEY` not configured on server)
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
