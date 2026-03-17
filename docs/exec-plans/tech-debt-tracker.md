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
| None currently. | - | - | - | Keep auth and role documentation aligned with `kb-server/app/core/auth.py`. |

## Recently Closed

| Item | Closed On | Notes |
| --- | --- | --- |
| Derive actor identity from hashed API keys | 2026-03-12 | Replaced caller-declared `source` routing with DB-backed API keys, role-based authorization, and a deprecated legacy fallback for `KB_API_KEY`. |
| Normalize auth docs vs runtime behavior | 2026-03-07 | Aligned auth behavior in `kb-server/README.md` and `docs/SECURITY.md` with middleware in `kb-server/app/core/auth.py`. |
| Improve stale-doc auto-fix coverage | 2026-03-07 | Added `--autofix-last-verified` mode in `scripts/docs_garden.py` for stale metadata refresh before report generation. |
| Add docs checks to local pre-commit workflow | 2026-03-07 | Added `.pre-commit-config.yaml` with docs lint and generated-artifact hooks, documented in root README. |
