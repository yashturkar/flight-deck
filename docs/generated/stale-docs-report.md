---
owner: platform
status: generated
last_verified: 2026-10-05
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

Generated: `2026-10-05`

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
| `AGENTS.md` | `platform` | 198 |
| `ARCHITECTURE.md` | `architecture` | 191 |
| `docs/CLIENTS.md` | `client` | 191 |
| `docs/DESIGN.md` | `architecture` | 182 |
| `docs/PLANS.md` | `platform` | 198 |
| `docs/PRODUCT_SENSE.md` | `product` | 182 |
| `docs/QUALITY_SCORE.md` | `platform` | 198 |
| `docs/RELIABILITY.md` | `sre` | 191 |
| `docs/SECURITY.md` | `security` | 191 |
| `docs/design-docs/core-beliefs.md` | `architecture` | 182 |
| `docs/design-docs/index.md` | `architecture` | 191 |
| `docs/design-docs/source-map.md` | `platform` | 198 |
| `docs/exec-plans/active/README.md` | `platform` | 168 |
| `docs/exec-plans/completed/README.md` | `platform` | 182 |
| `docs/exec-plans/completed/context-system-rollout.md` | `platform` | 182 |
| `docs/exec-plans/tech-debt-tracker.md` | `platform` | 198 |
| `docs/index.md` | `platform` | 198 |
| `docs/product-specs/index.md` | `product` | 191 |
| `docs/product-specs/kb-server.md` | `backend` | 198 |
| `docs/product-specs/vault-sync.md` | `client` | 198 |
| `docs/runbooks/autonomous-agent-e2e.md` | `platform` | 198 |
| `docs/runbooks/backup-restore.md` | `sre` | 182 |
| `docs/runbooks/deployment.md` | `sre` | 191 |
| `docs/runbooks/incident-response.md` | `sre` | 198 |

## Missing or Invalid Metadata

- none

## Suggested Actions

- refresh stale docs and update `last_verified`
- correct frontmatter schema mismatches
- convert repeated stale docs into tracked debt items
