---
owner: platform
status: draft
last_verified: 2026-03-14
source_of_truth:
  - exec-plans/completed/context-system-rollout.md
related_code:
  - ../scripts/docs_lint.py
  - ../scripts/generate_context_artifacts.py
related_tests:
  - ../kb-server/tests
  - ../vault-sync/tests
review_cycle_days: 14
---

# Plans

## Plan Types

- Lightweight plans for small changes and low-risk edits.
- Execution plans for multi-step, cross-domain work.

## Plan Locations

- Active: `exec-plans/active/`
- Completed: `exec-plans/completed/`
- Debt register: `exec-plans/tech-debt-tracker.md`

## Current Focus

- Context system rollout is complete: `exec-plans/completed/context-system-rollout.md`.
- Current work should be tracked as reliability hardening and docs-automation debt in `exec-plans/tech-debt-tracker.md`.

## Regeneration Commands

Generated context artifacts:

```bash
python3 scripts/generate_context_artifacts.py
```

Documentation checks:

```bash
python3 scripts/docs_lint.py
python3 scripts/docs_changed_guard.py --base origin/main --head HEAD
python3 scripts/docs_garden.py --output docs/generated/stale-docs-report.md
```

## Autonomous Feature Validation

For local validation of role-based API keys, `vault-sync`, and the tmux-based
runtime, use:

- `runbooks/local-role-auth-e2e.md`
