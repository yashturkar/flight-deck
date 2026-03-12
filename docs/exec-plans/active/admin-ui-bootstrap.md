---
owner: platform
status: draft
last_verified: 2026-03-12
source_of_truth:
  - ../../../kb-server/AGENTS.md
  - ../../../kb-server/app/main.py
  - ../../../kb-server/app/core/config.py
related_code:
  - ../../../kb-server/app/api/routes
  - ../../../kb-server/app/services
related_tests:
  - ../../../kb-server/tests
review_cycle_days: 14
---

# Admin UI Bootstrap

## Objective

Add an initial admin surface to `kb-server` for setup, configuration, and operational visibility without changing the core note-writing workflow.

## First Slice

Ship a minimal but real `/admin` experience that provides:

- current configuration visibility for key settings
- write support for local `.env` configuration updates
- write-only secret update inputs for `KB_API_KEY` and `GITHUB_TOKEN`
- readiness and vault/git status summary
- recent jobs, vault events, and publish runs
- visibility into pending `kb-api/*` PR state when GitHub is configured

## Non-Goals

- no note editing UI
- no browser-triggered host provisioning
- no direct mutation of PR approval semantics
- no requirement to store secrets in `.env`

## Design Constraints

- The admin UI is an operator surface layered on top of existing API and worker behavior.
- Existing API-key middleware remains in force when `KB_API_KEY` is configured.
- Secret values are never returned in API responses after save.
- Config writes update `.env`, but operators should be told that process restart may be required for full effect.
- The UI should degrade cleanly when GitHub is unconfigured or the vault/db is unavailable.

## Delivery Plan

1. Add admin service helpers for status aggregation and `.env` persistence.
2. Add `/admin`, `/admin/api/state`, and `/admin/api/config`.
3. Render a lightweight in-app dashboard with setup and status sections.
4. Add focused tests for config persistence and admin endpoints.
5. Update README with usage and restart expectations.
