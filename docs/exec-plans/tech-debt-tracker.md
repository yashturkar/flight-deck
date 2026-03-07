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
| Improve stale-doc auto-fix coverage | docs-automation | low | platform | extend docs_garden script |
| Add docs checks to local pre-commit workflow | devex | low | platform | evaluate pre-commit adoption |

## Recently Closed

| Item | Closed On | Notes |
| --- | --- | --- |
| Normalize auth docs vs runtime behavior | 2026-03-07 | Aligned auth behavior in `kb-server/README.md` and `docs/SECURITY.md` with middleware in `kb-server/app/core/auth.py`. |
