---
owner: platform
status: generated
last_verified: 2026-03-30
source_of_truth:
  - ../../scripts/docs_garden.py
related_code:
  - ../../scripts/docs_lint.py
related_tests:
  - ../../kb-server/tests
  - ../../vault-sync/tests
review_cycle_days: 7
---

# Stale Documentation Report

Generated: `2026-03-30`

## Ownership Summary

| Owner | Document Count |
| --- | --- |
| `architecture` | 4 |
| `backend` | 1 |
| `client` | 2 |
| `platform` | 13 |
| `product` | 2 |
| `security` | 1 |
| `sre` | 4 |

## Stale Docs

| File | Owner | Days Over SLA |
| --- | --- | --- |
| `AGENTS.md` | `platform` | 9 |
| `ARCHITECTURE.md` | `architecture` | 2 |
| `docs/CLIENTS.md` | `client` | 2 |
| `docs/PLANS.md` | `platform` | 9 |
| `docs/QUALITY_SCORE.md` | `platform` | 9 |
| `docs/RELIABILITY.md` | `sre` | 2 |
| `docs/SECURITY.md` | `security` | 2 |
| `docs/design-docs/index.md` | `architecture` | 2 |
| `docs/design-docs/source-map.md` | `platform` | 9 |
| `docs/exec-plans/tech-debt-tracker.md` | `platform` | 9 |
| `docs/index.md` | `platform` | 9 |
| `docs/product-specs/index.md` | `product` | 2 |
| `docs/product-specs/kb-server.md` | `backend` | 9 |
| `docs/product-specs/vault-sync.md` | `client` | 9 |
| `docs/runbooks/autonomous-agent-e2e.md` | `platform` | 9 |
| `docs/runbooks/deployment.md` | `sre` | 2 |
| `docs/runbooks/incident-response.md` | `sre` | 9 |

## Missing or Invalid Metadata

- none

## Suggested Actions

- refresh stale docs and update `last_verified`
- correct frontmatter schema mismatches
- convert repeated stale docs into tracked debt items
