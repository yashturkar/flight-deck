---
owner: architecture
status: verified
last_verified: 2026-03-07
source_of_truth:
  - kb-server/app/main.py
  - kb-server/app/api/routes/notes.py
  - kb-server/app/services/current_view_service.py
  - vault-sync/vault_sync/sync.py
related_code:
  - kb-server/app/services/git_batcher.py
  - kb-server/app/workers/autosave.py
  - vault-sync/vault_sync/watcher.py
related_tests:
  - kb-server/tests/test_current_view.py
  - kb-server/tests/test_source_and_delete.py
  - vault-sync/tests/test_sync.py
review_cycle_days: 21
---

# Flight Deck Architecture

## Monorepo Topology

- `kb-server/`: authoritative API and worker processes.
- `vault-sync/`: local daemon that mirrors and edits through API.
- `docs/`: system-of-record documentation for humans and agents.
- `scripts/`: repository-level automation for docs quality and generation.

## Runtime Operations

- Current operations standard runs `kb-api` + `kb-worker` in `tmux`.
- Planned operations target is `systemctl`-managed services.
- Full autonomous integration workflow is documented in:
  - `docs/runbooks/autonomous-agent-e2e.md`

## Domain Boundaries

### kb-server

- Exposes health/readiness and notes/publish APIs.
- Enforces path + extension safety for note files.
- Routes writes by source:
  - `source=api`: queued to PR branch workflow.
  - `source=human`: direct commit/push to base branch.
- Implements `view=current` as composed, read-only view.

### vault-sync

- Pulls notes from `view=current`.
- Watches local filesystem for edits/deletes.
- Pushes local changes as `source=human`.
- Periodically repulls to converge and absorb pending+approved state.

## Core Flows

### API/Agent Write Flow

1. Client writes note (`source=api`, `view=main`).
2. Server writes file and enqueues path in batcher.
3. Batcher commits to `kb-api/YYYY-MM-DD`.
4. Branch is pushed and PR is created/updated.
5. Content enters `main` only on PR merge.

### Human Write Flow

1. Human edit is observed locally or via sync client.
2. Server receives `source=human`.
3. File change is committed directly to configured base branch.
4. Optional publish actions run from worker flow.

### Current View Read Flow

1. Read request uses `view=current`.
2. Service overlays `main` with open `kb-api/*` branches.
3. API returns composed content + source branches.
4. Writes to `view=current` are rejected.

## Invariants

- `main` remains approved truth.
- Agent/API changes are reviewable by PR.
- Current view is for visibility, not unscoped edits.
- Docs in `docs/` must track these invariants and link to code/tests.

## Related Docs

- `AGENTS.md`
- `docs/design-docs/index.md`
- `docs/product-specs/kb-server.md`
- `docs/product-specs/vault-sync.md`
- `docs/SECURITY.md`
- `docs/RELIABILITY.md`

