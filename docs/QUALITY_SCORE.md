---
owner: platform
status: draft
last_verified: 2026-03-07
source_of_truth:
  - design-docs/source-map.md
related_code:
  - ../scripts/docs_lint.py
related_tests:
  - ../kb-server/tests
  - ../vault-sync/tests
review_cycle_days: 14
---

# Quality Score

## Scoring Model

Each domain is scored 0-5 across:

- **Coverage**: required docs exist and link to code/tests.
- **Freshness**: `last_verified` within `review_cycle_days`.
- **Correctness**: docs align with current behavior.
- **Operability**: runbooks and plans are actionable.

## Domain Scorecard

| Domain | Coverage | Freshness | Correctness | Operability | Notes |
| --- | --- | --- | --- | --- | --- |
| kb-server | 3 | 3 | 3 | 3 | Baseline established; automate generated references next. |
| vault-sync | 3 | 3 | 3 | 2 | Add deeper failure-mode runbook details. |
| cross-cutting | 2 | 3 | 3 | 2 | CI checks added; gardening loop to improve over time. |

## Automation Ownership

- `docs-context` CI (`.github/workflows/docs-context.yml`) is owned by platform and must stay required on PRs.
- `docs-garden` scheduled maintenance (`.github/workflows/docs-garden.yml`) is owned by platform and runs weekly on Mondays at 06:17 UTC.
- Weekly review must confirm latest `docs/generated/stale-docs-report.md` results are triaged.

## Cadence

- Weekly: review active plans and changed invariants.
- Monthly: update scorecard and stale-doc burndown.
- Quarterly: reassess rubric thresholds and ownership fit.
