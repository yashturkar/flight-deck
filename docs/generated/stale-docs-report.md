---
owner: platform
status: generated
last_verified: 2026-04-27
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

Generated: `2026-04-27`

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
| `AGENTS.md` | `platform` | 37 |
| `ARCHITECTURE.md` | `architecture` | 30 |
| `docs/CLIENTS.md` | `client` | 30 |
| `docs/DESIGN.md` | `architecture` | 21 |
| `docs/PLANS.md` | `platform` | 37 |
| `docs/PRODUCT_SENSE.md` | `product` | 21 |
| `docs/QUALITY_SCORE.md` | `platform` | 37 |
| `docs/RELIABILITY.md` | `sre` | 30 |
| `docs/SECURITY.md` | `security` | 30 |
| `docs/design-docs/core-beliefs.md` | `architecture` | 21 |
| `docs/design-docs/index.md` | `architecture` | 30 |
| `docs/design-docs/source-map.md` | `platform` | 37 |
| `docs/exec-plans/active/README.md` | `platform` | 7 |
| `docs/exec-plans/completed/README.md` | `platform` | 21 |
| `docs/exec-plans/completed/context-system-rollout.md` | `platform` | 21 |
| `docs/exec-plans/tech-debt-tracker.md` | `platform` | 37 |
| `docs/index.md` | `platform` | 37 |
| `docs/product-specs/index.md` | `product` | 30 |
| `docs/product-specs/kb-server.md` | `backend` | 37 |
| `docs/product-specs/vault-sync.md` | `client` | 37 |
| `docs/runbooks/autonomous-agent-e2e.md` | `platform` | 37 |
| `docs/runbooks/backup-restore.md` | `sre` | 21 |
| `docs/runbooks/deployment.md` | `sre` | 30 |
| `docs/runbooks/incident-response.md` | `sre` | 37 |

## Missing or Invalid Metadata

- none

## Suggested Actions

- refresh stale docs and update `last_verified`
- correct frontmatter schema mismatches
- convert repeated stale docs into tracked debt items
