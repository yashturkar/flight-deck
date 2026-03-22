---
owner: platform
status: generated
last_verified: 2026-03-22
source_of_truth:
  - ../../kb-server/app/api/routes/health.py
  - ../../kb-server/app/api/routes/notes.py
  - ../../kb-server/app/api/routes/publish.py
related_code:
  - ../../scripts/generate_context_artifacts.py
related_tests:
  - ../../kb-server/tests
review_cycle_days: 7
---

# API Surface (Generated)

Generated on `2026-03-22` from route handlers.

| Method | Path |
| --- | --- |
| `GET` | `/health` |
| `GET` | `/ready` |
| `GET` | `/` |
| `GET` | `/{path:path}` |
| `PUT` | `/{path:path}` |
| `DELETE` | `/{path:path}` |
| `POST` | `/publish` |

Do not edit manually. Regenerate with `python3 scripts/generate_context_artifacts.py`.