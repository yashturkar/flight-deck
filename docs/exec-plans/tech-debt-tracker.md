---
owner: platform
status: draft
last_verified: 2026-03-07
source_of_truth:
  - completed/context-system-rollout.md
related_code:
  - ../../kb-server/app/api/routes/notes.py
  - ../../kb-server/app/main.py
related_tests:
  - ../../kb-server/tests
review_cycle_days: 14
---

# Tech Debt Tracker

## Open Items

| Item | Area | Severity | Owner | Next Action |
| --- | --- | --- | --- | --- |
| Actor identity is caller-declared via `source` query param instead of derived from auth | security | high | backend | Implement per-actor API keys or tokens so the server enforces USER vs AGENT identity. See `docs/SECURITY.md` and `docs/product-specs/kb-server.md` TODOs. |

## Recently Closed

| Item | Closed On | Notes |
| --- | --- | --- |
| Normalize auth docs vs runtime behavior | 2026-03-07 | Aligned auth behavior in `kb-server/README.md` and `docs/SECURITY.md` with middleware in `kb-server/app/core/auth.py`. |
| Improve stale-doc auto-fix coverage | 2026-03-07 | Added `--autofix-last-verified` mode in `scripts/docs_garden.py` for stale metadata refresh before report generation. |
| Add docs checks to local pre-commit workflow | 2026-03-07 | Added `.pre-commit-config.yaml` with docs lint and generated-artifact hooks, documented in root README. |
