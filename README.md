# AgentGuard

> **Status: mothballed as a standalone product, effective 2026-08-30.**

This repository is retained for preservation and bounded asset extraction. It is not approved for new standalone feature development, customer acquisition, deployment, or production workloads. This change does not prove that any historical runtime or cloud resource has been shut down; external runtime state remains unverified.

## Portfolio Disposition

- Preserve reusable attack libraries, detector ideas, finance policy rules, and security-audit concepts.
- Extract selected assets into RedTeamAI assurance work or an active product only when a named consumer and acceptance test exist.
- Do not revive the proxy, dashboard, marketplace, billing, SDK, or deployment platform by default.
- Keep historical product material and deployment workflows available for reference without allowing automatic execution.

The machine-readable authority is [`PROJECT_STATUS.json`](PROJECT_STATUS.json). The extraction inventory and caveats are in [`docs/ARCHIVE_AND_ASSET_MAP.md`](docs/ARCHIVE_AND_ASSET_MAP.md).

## Preserved Assets

| Asset | Source | Intended disposition |
|---|---|---|
| Red-team mutations and attack sequences | `agentguard-backend/backend/app/services/red_team_engine.py` | Highest-priority candidate for RedTeamAI extraction |
| Adversarial stress corpus | `agentguard-backend/backend/app/services/stress_test_service.py` | Extract test cases only; remove database and readiness-score coupling |
| Detector implementations | `agentguard-backend/backend/app/services/detection/` | Evaluate individually against a measured corpus before adoption |
| Finance policy patterns | `agentguard-backend/backend/app/services/policy_classifier_service.py` | Extract pure rules only; keep reporting/database concerns separate |
| Security-audit concepts | `security-audit/` | Reuse checks selectively; do not inherit skip-as-success behavior |

## Allowed Work

- Preservation, dependency metadata maintenance, and security fixes needed to keep archived assets safe.
- Read-only evaluation and provenance review.
- Small extraction pull requests with a named destination, owner, tests, and rollback.

## Reactivation

Standalone development requires a new explicit portfolio decision and every gate in `PROJECT_STATUS.json`: a committed design partner, validated differentiation, an independently reviewed security baseline, and credible unit economics. Historical workflows must not be restored wholesale.

## Historical Material

- Former standalone README: [`docs/historical/STANDALONE_PRODUCT_README.md`](docs/historical/STANDALONE_PRODUCT_README.md)
- Former GitHub workflows: [`docs/historical/workflows/`](docs/historical/workflows/)
- Archive hardening lane: `codex/p0-release-truth` is limited to security and truth-maintenance work for dormant source. A reviewed merge from that lane does not reactivate the product or authorize deployment, provider traffic, registration, or customer use.
