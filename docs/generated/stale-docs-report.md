---
owner: platform
status: generated
last_verified: 2026-09-07
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

Generated: `2026-09-07`

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
| `AGENTS.md` | `platform` | 170 |
| `ARCHITECTURE.md` | `architecture` | 163 |
| `docs/CLIENTS.md` | `client` | 163 |
| `docs/DESIGN.md` | `architecture` | 154 |
| `docs/PLANS.md` | `platform` | 170 |
| `docs/PRODUCT_SENSE.md` | `product` | 154 |
| `docs/QUALITY_SCORE.md` | `platform` | 170 |
| `docs/RELIABILITY.md` | `sre` | 163 |
| `docs/SECURITY.md` | `security` | 163 |
| `docs/design-docs/core-beliefs.md` | `architecture` | 154 |
| `docs/design-docs/index.md` | `architecture` | 163 |
| `docs/design-docs/source-map.md` | `platform` | 170 |
| `docs/exec-plans/active/README.md` | `platform` | 140 |
| `docs/exec-plans/completed/README.md` | `platform` | 154 |
| `docs/exec-plans/completed/context-system-rollout.md` | `platform` | 154 |
| `docs/exec-plans/tech-debt-tracker.md` | `platform` | 170 |
| `docs/index.md` | `platform` | 170 |
| `docs/product-specs/index.md` | `product` | 163 |
| `docs/product-specs/kb-server.md` | `backend` | 170 |
| `docs/product-specs/vault-sync.md` | `client` | 170 |
| `docs/runbooks/autonomous-agent-e2e.md` | `platform` | 170 |
| `docs/runbooks/backup-restore.md` | `sre` | 154 |
| `docs/runbooks/deployment.md` | `sre` | 163 |
| `docs/runbooks/incident-response.md` | `sre` | 170 |

## Missing or Invalid Metadata

- none

## Suggested Actions

- refresh stale docs and update `last_verified`
- correct frontmatter schema mismatches
- convert repeated stale docs into tracked debt items
