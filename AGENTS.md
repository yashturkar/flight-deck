---
owner: platform
status: verified
last_verified: 2026-03-07
source_of_truth:
  - ARCHITECTURE.md
  - docs/design-docs/index.md
related_code:
  - kb-server/app/main.py
  - kb-server/app/api/routes/notes.py
  - kb-server/app/services/current_view_service.py
  - vault-sync/vault_sync/sync.py
related_tests:
  - kb-server/tests
  - vault-sync/tests
review_cycle_days: 14
---

# Flight Deck Agent Map

This file is the entry point for agents. It is intentionally short.

## Start Here

1. Read `ARCHITECTURE.md` for domain boundaries.
2. Read `docs/design-docs/index.md` for design invariants.
3. Pick a domain:
  - `kb-server`: API, Git workflows, current-view composition.
  - `mcp-server`: MCP adapter for structured agent access to notes and context bundles.
  - `vault-sync`: local mirror and push/pull convergence.
4. Read topical constraints before implementation:
  - `docs/SECURITY.md`
  - `docs/RELIABILITY.md`
  - `docs/QUALITY_SCORE.md`
5. Use execution plans for non-trivial work:
  - `docs/exec-plans/active/`
  - `docs/exec-plans/completed/`

## Domain Maps

- Backend domain: `docs/product-specs/kb-server.md`
- MCP adapter domain: `docs/product-specs/mcp-server.md`
- Sync client domain: `docs/product-specs/vault-sync.md`
- Branching + current view model: `kb-server/BRANCHING_AND_CURRENT_VIEW.md`

## Source of Truth Policy

- Code behavior is canonical.
- Tests are executable specs and break ties when docs drift.
- Docs in `docs/` are the maintained knowledge store.
- Subproject READMEs are operational references and should link back into `docs/`.

## Read/Write Semantics You Must Preserve

- `main` is approved content.
- `kb-api/*` branches carry pending API/agent changes via PRs.
- `view=current` is read-only composed state.
- Human-origin writes (`source=human`) commit directly to base branch.

See:

- `docs/design-docs/core-beliefs.md`
- `docs/product-specs/kb-server.md`
- `docs/references/harness-engineering-notes.txt`

## When To Update Docs

Update docs in the same PR when changing:

- API request/response semantics.
- Auth behavior, trust boundaries, or secrets handling.
- Git branch ownership or merge flow.
- Sync convergence behavior and failure handling.
- Deployment, backup/restore, or runbook steps.

## Mechanical Checks

- `scripts/docs_lint.py` validates structure, metadata, and links.
- `scripts/docs_changed_guard.py` enforces code-to-doc touch policy in PRs.
- `scripts/generate_context_artifacts.py` refreshes generated reference docs.
- `scripts/docs_garden.py` reports stale docs and creates an action plan.

## Fast Navigation

- Architecture: `ARCHITECTURE.md`
- Design index: `docs/design-docs/index.md`
- Plans index: `docs/PLANS.md`
- Security: `docs/SECURITY.md`
- Reliability: `docs/RELIABILITY.md`
- Autonomous E2E workflow: `docs/runbooks/autonomous-agent-e2e.md`
