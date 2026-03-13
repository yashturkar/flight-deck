---
owner: platform
status: generated
last_verified: 2026-03-12
source_of_truth:
  - ../../kb-server/app/api/routes/health.py
  - ../../kb-server/app/api/routes/notes.py
  - ../../kb-server/app/api/routes/publish.py
  - ../../kb-server/app/api/routes/admin.py
related_code:
  - ../../scripts/generate_context_artifacts.py
related_tests:
  - ../../kb-server/tests
review_cycle_days: 7
---

# API Surface (Generated)

Generated on `2026-03-12` from route handlers.

| Method | Path |
| --- | --- |
| `GET` | `/health` |
| `GET` | `/ready` |
| `GET` | `/` |
| `GET` | `/{path:path}` |
| `PUT` | `/{path:path}` |
| `DELETE` | `/{path:path}` |
| `POST` | `/publish` |
| `GET` | `/admin` |
| `GET` | `/admin/api/state` |
| `POST` | `/admin/api/config` |
| `POST` | `/admin/api/start` |
| `POST` | `/admin/api/restart` |
| `POST` | `/admin/api/start-worker` |
| `POST` | `/admin/api/restart-worker` |

Do not edit manually. Regenerate with `python3 scripts/generate_context_artifacts.py`.