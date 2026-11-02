---
owner: platform
status: generated
last_verified: 2026-11-02
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

Generated: `2026-11-02`

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
| `AGENTS.md` | `platform` | 226 |
| `ARCHITECTURE.md` | `architecture` | 219 |
| `docs/CLIENTS.md` | `client` | 219 |
| `docs/DESIGN.md` | `architecture` | 210 |
| `docs/PLANS.md` | `platform` | 226 |
| `docs/PRODUCT_SENSE.md` | `product` | 210 |
| `docs/QUALITY_SCORE.md` | `platform` | 226 |
| `docs/RELIABILITY.md` | `sre` | 219 |
| `docs/SECURITY.md` | `security` | 219 |
| `docs/design-docs/core-beliefs.md` | `architecture` | 210 |
| `docs/design-docs/index.md` | `architecture` | 219 |
| `docs/design-docs/source-map.md` | `platform` | 226 |
| `docs/exec-plans/active/README.md` | `platform` | 196 |
| `docs/exec-plans/completed/README.md` | `platform` | 210 |
| `docs/exec-plans/completed/context-system-rollout.md` | `platform` | 210 |
| `docs/exec-plans/tech-debt-tracker.md` | `platform` | 226 |
| `docs/index.md` | `platform` | 226 |
| `docs/product-specs/index.md` | `product` | 219 |
| `docs/product-specs/kb-server.md` | `backend` | 226 |
| `docs/product-specs/vault-sync.md` | `client` | 226 |
| `docs/runbooks/autonomous-agent-e2e.md` | `platform` | 226 |
| `docs/runbooks/backup-restore.md` | `sre` | 210 |
| `docs/runbooks/deployment.md` | `sre` | 219 |
| `docs/runbooks/incident-response.md` | `sre` | 226 |

## Missing or Invalid Metadata

- none

## Suggested Actions

- refresh stale docs and update `last_verified`
- correct frontmatter schema mismatches
- convert repeated stale docs into tracked debt items
