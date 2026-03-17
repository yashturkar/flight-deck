---
owner: backend
status: verified
last_verified: 2026-03-07
source_of_truth:
  - ../../kb-server/app/api/routes/notes.py
  - ../../kb-server/app/services/current_view_service.py
  - ../../kb-server/app/core/config.py
related_code:
  - ../../kb-server/app/services/git_batcher.py
  - ../../kb-server/app/workers/autosave.py
related_tests:
  - ../../kb-server/tests/test_current_view.py
  - ../../kb-server/tests/test_source_and_delete.py
review_cycle_days: 14
---

# Product Spec: kb-server

## Purpose

Provide a file-first API over a Git-backed vault with explicit approval boundaries.

## User-Visible Behavior

- `GET /notes` and `GET /notes/{path}` support:
  - `view=main` (default approved state)
  - `view=current` (approved + pending composed state)
- `PUT /notes/{path}` and `DELETE /notes/{path}` require an authenticated write-capable API key.
- Writes to `view=current` are rejected.

## Approval Model

- `agent`-role API keys batch changes to daily `kb-api/*` branches and PRs.
- `user` and `admin` API keys commit changes to the base branch directly.
- `readonly` API keys can read but cannot write or publish.
- `user`/`admin` Git commits and pushes use the configured USER identity.
- `agent` Git commits, pushes, and PR API calls use the configured AGENT identity.
- Mainline approval remains controlled by maintainers.

## Guardrails

- Allowed file extensions: `.md`, `.markdown`, `.txt`.
- No absolute paths and no traversal outside vault root.
- API key auth is enforced on all routes except `/health` and `/ready`.
- `KB_API_KEY` remains as a deprecated fallback only while no DB-backed keys exist.

## Related Operational Docs

- `../../kb-server/README.md`
- `../../kb-server/BRANCHING_AND_CURRENT_VIEW.md`
- `../SECURITY.md`
- `../RELIABILITY.md`
