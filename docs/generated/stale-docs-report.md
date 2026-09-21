---
owner: platform
status: generated
last_verified: 2026-09-21
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

Generated: `2026-09-21`

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
| `AGENTS.md` | `platform` | 184 |
| `ARCHITECTURE.md` | `architecture` | 177 |
| `docs/CLIENTS.md` | `client` | 177 |
| `docs/DESIGN.md` | `architecture` | 168 |
| `docs/PLANS.md` | `platform` | 184 |
| `docs/PRODUCT_SENSE.md` | `product` | 168 |
| `docs/QUALITY_SCORE.md` | `platform` | 184 |
| `docs/RELIABILITY.md` | `sre` | 177 |
| `docs/SECURITY.md` | `security` | 177 |
| `docs/design-docs/core-beliefs.md` | `architecture` | 168 |
| `docs/design-docs/index.md` | `architecture` | 177 |
| `docs/design-docs/source-map.md` | `platform` | 184 |
| `docs/exec-plans/active/README.md` | `platform` | 154 |
| `docs/exec-plans/completed/README.md` | `platform` | 168 |
| `docs/exec-plans/completed/context-system-rollout.md` | `platform` | 168 |
| `docs/exec-plans/tech-debt-tracker.md` | `platform` | 184 |
| `docs/index.md` | `platform` | 184 |
| `docs/product-specs/index.md` | `product` | 177 |
| `docs/product-specs/kb-server.md` | `backend` | 184 |
| `docs/product-specs/vault-sync.md` | `client` | 184 |
| `docs/runbooks/autonomous-agent-e2e.md` | `platform` | 184 |
| `docs/runbooks/backup-restore.md` | `sre` | 168 |
| `docs/runbooks/deployment.md` | `sre` | 177 |
| `docs/runbooks/incident-response.md` | `sre` | 184 |

## Missing or Invalid Metadata

- none

## Suggested Actions

- refresh stale docs and update `last_verified`
- correct frontmatter schema mismatches
- convert repeated stale docs into tracked debt items
