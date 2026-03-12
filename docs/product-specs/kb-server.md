---
owner: backend
status: verified
last_verified: 2026-03-07
source_of_truth:
  - ../../kb-server/app/api/routes/notes.py
  - ../../kb-server/app/api/routes/admin.py
  - ../../kb-server/app/services/current_view_service.py
  - ../../kb-server/app/core/config.py
related_code:
  - ../../kb-server/app/services/git_batcher.py
  - ../../kb-server/app/services/admin_service.py
  - ../../kb-server/app/workers/autosave.py
related_tests:
  - ../../kb-server/tests/test_current_view.py
  - ../../kb-server/tests/test_admin.py
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
- `PUT /notes/{path}` and `DELETE /notes/{path}` support:
  - `source=api` for PR-based pending writes
  - `source=human` for direct approved writes
- Writes to `view=current` are rejected.
- `GET /admin` exposes an operator-facing setup and status surface.
- `GET /admin/api/state` returns admin config/status state for the local instance.
- `POST /admin/api/config` writes local configuration updates to `kb-server/.env`.
- `GET /admin/login`, `POST /admin/session`, and `POST /admin/logout` support browser access to the admin surface when API-key auth is enabled.

## Approval Model

- API-origin changes are batched to daily `kb-api/*` branches and PRs.
- Human-origin changes go to base branch directly.
- Mainline approval remains controlled by maintainers.
- The admin UI is not a note-editing surface and does not bypass PR-based approval for content changes.

## Guardrails

- Allowed file extensions: `.md`, `.markdown`, `.txt`.
- No absolute paths and no traversal outside vault root.
- API key auth enforced when configured.
- Admin config writes are local instance management actions only; operators must still provision the DB, vault repo, and host runtime outside the browser.
- Process environment variables override `.env`, including when `.env` is edited through `/admin`.

## Related Operational Docs

- `../../kb-server/README.md`
- `../../kb-server/BRANCHING_AND_CURRENT_VIEW.md`
- `../SECURITY.md`
- `../RELIABILITY.md`
