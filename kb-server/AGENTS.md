# KB Server - Agent Instructions

This document provides context and instructions for AI agents working on the kb-server codebase.

## Project Overview

KB Server is a file-first knowledge base server that:
- Watches a Markdown vault directory for changes
- Auto-commits and pushes human edits to Git (autosave worker)
- Provides a REST API for programmatic note CRUD
- API writes go through a PR workflow (daily branch + GitHub PR)
- Optionally triggers Quartz static site builds

## Architecture

```
kb-server/
├── app/
│   ├── api/routes/       # FastAPI route handlers
│   │   ├── health.py     # /health, /ready endpoints
│   │   ├── notes.py      # /notes CRUD endpoints
│   │   └── publish.py    # /publish endpoint
│   ├── core/
│   │   ├── config.py     # Pydantic settings (env vars)
│   │   └── auth.py       # API key authentication
│   ├── models/
│   │   └── db.py         # SQLAlchemy models (Job, VaultEvent, PublishRun)
│   ├── services/
│   │   ├── git_service.py    # Git CLI wrapper
│   │   ├── git_batcher.py    # Debounced batch commit + PR for API writes
│   │   ├── github_service.py # GitHub API client for PR management
│   │   ├── vault_service.py  # File read/write operations
│   │   └── publish_service.py # Quartz build triggering
│   ├── workers/
│   │   └── autosave.py   # File watcher for human edits
│   └── main.py           # FastAPI app factory
├── alembic/              # Database migrations
├── tests/                # Pytest test suite
└── scripts/              # Setup and deployment scripts
```

## Key Workflows

### 1. API Write Flow (PR-based)

When a client calls `PUT /notes/{path}`:
1. File is written to vault
2. Path is enqueued to `GitBatcher`
3. After debounce (default 10s), batcher:
   - Checks out daily branch (`kb-api/YYYY-MM-DD`)
   - Commits all batched changes (including deletions)
   - Pushes branch to remote
   - Creates/updates PR via GitHub API
4. Changes go to main only after PR is merged

### 2. Autosave Flow (direct push)

When a human edits files in the vault:
1. File watcher detects changes
2. After debounce, commits and pushes directly to main
3. Optionally triggers Quartz rebuild

### 3. Periodic Pull (sync merged PRs)

The autosave worker also runs a periodic pull (default every 60s):
1. Pulls from `origin/main` using `--ff-only`
2. Syncs any merged PRs back to the local vault
3. Skips if there are uncommitted local changes

### 4. Deletion Tracking

Both workflows use `git add --all` which stages:
- New files
- Modified files
- Deleted files

Deletions in the local vault are reflected in commits/PRs.

## Configuration

Key environment variables (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `VAULT_PATH` | Path to the Git-initialized vault directory |
| `DATABASE_URL` | PostgreSQL connection string |
| `KB_API_KEY` | API authentication key |
| `GIT_REMOTE` / `GIT_BRANCH` | Git remote and base branch |
| `GITHUB_TOKEN` | GitHub PAT for PR creation (needs `repo` scope) |
| `GITHUB_REPO` | Repository in `owner/repo` format |
| `GIT_BATCH_DEBOUNCE_SECONDS` | Delay before committing API writes |
| `GIT_BATCH_BRANCH_PREFIX` | Prefix for daily branches (default: `kb-api`) |

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Always 200 |
| GET | `/ready` | No | 200 when DB and vault reachable |
| GET | `/notes/` | Yes | List notes (optional `?prefix=`) |
| GET | `/notes/{path}` | Yes | Read a note |
| PUT | `/notes/{path}` | Yes | Write/create a note |
| POST | `/publish` | Yes | Trigger Quartz build |

## Testing

```bash
# Run all tests
python3 -m pytest -v

# Run specific test files
python3 -m pytest tests/test_git_service.py tests/test_git_batcher.py

# Tests use temporary directories and SQLite - no external deps needed
```

## Common Tasks

### Adding a new API endpoint

1. Create route handler in `app/api/routes/`
2. Add router to `app/main.py`
3. Add tests in `tests/`

### Modifying Git workflow

- `git_service.py` - Low-level Git CLI operations
- `git_batcher.py` - Batching logic and PR workflow
- `github_service.py` - GitHub API interactions

### Adding new config options

1. Add field to `Settings` class in `app/core/config.py`
2. Document in `.env.example`
3. Update `README.md` environment variables table

## Logged Proposals

### Admin / Management Web UI

Requested scope:
- Initial setup flow for required configuration
- UI for viewing and editing relevant configuration values
- Vault and Git/repo configuration visibility
- Status dashboard for API, worker, health, jobs, and recent failures
- Visibility into pending PR workflow state and recent automation activity

Intent:
- This is an admin surface for setup, operations, and debugging
- This is not a content editing UI for notes
- Content-affecting actions must continue to respect the PR-based workflow where applicable

Recommended rollout:
1. Read-only admin dashboard
   - Health/readiness
   - Config validation results
   - Vault/Git status summary
   - Recent jobs, errors, publish runs, and worker activity
2. Setup + config management
   - Guided first-run setup for `VAULT_PATH`, `DATABASE_URL`, `GITHUB_REPO`, branch settings, and optional auth config
   - Editable non-secret config with validation
3. Workflow visibility
   - Pending batched changes
   - Open `kb-api/*` branches / PR state
   - Recent sync/autosave/publish outcomes
4. Secret management
   - Prefer write-only secret updates
   - Do not casually echo `KB_API_KEY` or `GITHUB_TOKEN` back to the browser
   - Preserve support for process environment variables overriding `.env`

Implementation constraints:
- Treat the UI as an admin plane layered on top of existing API/worker behavior
- Do not silently provision system services or host-level dependencies from the browser
- Be explicit about which values are stored in `.env` versus provided by environment variables
- Add strong admin authentication before exposing any state-changing operational actions
- Update docs with the trust boundary and secret-handling model when implemented

Current bootstrap behavior:
- `/admin` is now available as an initial admin surface
- it shows config, readiness, vault/db/git status, recent jobs/events, and PR summary
- it can write `.env` updates for visible config fields
- it exposes write-only inputs for `KB_API_KEY` and `GITHUB_TOKEN`

Current operator flow:
1. Boot `kb-server` with enough config to start.
2. Open `/admin`.
3. Enter non-secret instance config such as `VAULT_PATH`, `DATABASE_URL`, and `GITHUB_REPO`.
4. Save config, which writes `kb-server/.env`.
5. Restart `kb-api` and `kb-worker`.
6. Reopen `/admin` and verify readiness and integration state.

Current limitations:
- `/admin` does not provision PostgreSQL, create DB roles, or create databases
- `/admin` does not create the notes repo or GitHub repo
- `/admin` does not restart services automatically
- host-level setup still happens outside the browser

Secret model:
- Preferred: establish `KB_API_KEY` and `GITHUB_TOKEN` as process environment variables
- Supported for local/dev use: save `KB_API_KEY` and `GITHUB_TOKEN` through the admin UI into `.env`
- Do not treat `GITHUB_REPO` as a secret; it should normally live in `.env`
- Process environment still overrides `.env`

Admin auth model:
- When `KB_API_KEY` is set, `/admin/login` accepts that same API key and stores it in an HTTP-only cookie for browser access to `/admin`
- The admin UI is therefore gated by the same shared secret as the API unless auth is disabled

## Dependencies

- Python 3.10+
- Git 2.34+
- PostgreSQL 15+
- GitHub token with `repo` scope (for API write workflow)

## File Constraints

- Allowed extensions: `.md`, `.markdown`, `.txt`
- Paths must be relative to vault
- No absolute paths or `..` traversal allowed

## Curl Examples

```bash
# List notes
curl -H "X-API-Key: $KB_API_KEY" "http://localhost:8000/notes/"

# Read a note
curl -H "X-API-Key: $KB_API_KEY" "http://localhost:8000/notes/notes/hello.md"

# Write a note
curl -X PUT \
  -H "X-API-Key: $KB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content":"# Hello\nContent here.\n"}' \
  "http://localhost:8000/notes/notes/hello.md"

# Trigger publish
curl -X POST -H "X-API-Key: $KB_API_KEY" "http://localhost:8000/publish"
```
