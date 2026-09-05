# AgentGuard Archive and Asset Map

## Decision

AgentGuard is mothballed as a standalone product as of 2026-08-30. The repository remains available as a source archive while selected assurance assets are evaluated for RedTeamAI or for an active product with a concrete consumer. The source baseline for this disposition is `07d83350ae7e21e50870232bda1a1923a10cf799`.

This is a source-control disposition, not production teardown evidence. Public endpoints, cloud accounts, images, databases, domains, secrets, and provider resources were not inspected or changed. Their state is unverified.

## Extraction Inventory

| Priority | Asset | Source | Coupling and risk | Extraction rule |
|---|---|---|---|---|
| 1 | Attack mutations, multi-turn sequences, and attack taxonomy | `agentguard-backend/backend/app/services/red_team_engine.py` | Mostly standard-library code. Taxonomy labels and attack prompts can become stale or produce unsafe test output. | Copy only with provenance, deterministic mutation tests, current taxonomy review, and an authorized-target boundary. |
| 2 | Adversarial stress corpus | `agentguard-backend/backend/app/services/stress_test_service.py` | Test cases share a module with SQLAlchemy, detector registries, organization state, and an unvalidated readiness score. | Extract corpus records into data fixtures. Do not copy the readiness score or database path without separate validation. |
| 3 | Detector implementations and common result types | `agentguard-backend/backend/app/services/detection/` | Implementations depend on AgentGuard enums, models, Celery paths, and registry behavior. Several detectors send payload-derived prompts through `app/services/llm_service.py` to configured OpenAI or Anthropic endpoints; this adds secret, privacy, provider-egress, spend, and provider-failure boundaries. The registry also contains pass-through stub fallbacks that can hide missing implementations. | Default to extracting pure rule-based portions only. An LLM-backed detector additionally requires an approved destination adapter, payload redaction policy, no-egress test, hard spend limit, deterministic provider-failure behavior, measured attack/benign corpora, and fail-closed registration. |
| 4 | Finance policy rules | `agentguard-backend/backend/app/services/policy_classifier_service.py` | Pure regex rules are mixed with incident queries and reporting. Rules are heuristics, not regulatory determinations. | Extract rule definitions and unit tests only. Label results as signals requiring review, not compliance proof. |
| 5 | Red-team API and persistence concepts | `agentguard-backend/backend/app/api/red_team.py`, `agentguard-backend/backend/app/models/red_team.py` | Coupled to AgentGuard authentication, RBAC, tenancy, database schema, and detection pipeline. | Use as design reference. Do not copy endpoints or tables without a destination-specific ownership and authorization model. |
| 6 | Threat-intelligence and governance concepts | `agentguard-backend/backend/app/api/threat_intel.py`, `agentguard-backend/backend/app/models/threat_intel.py`, `agentguard-backend/backend/app/api/governance_testing.py` | Product-specific lifecycle and tenant assumptions. External feed provenance is not established by this archive. | Re-derive the destination contract and provenance requirements before implementation. |
| 7 | Automated security checks | `security-audit/` | Product paths are hard-coded and missing tools are skipped. A generated report can therefore look complete while checks did not run. | Reuse individual checks only when required tools fail closed and outputs are machine-verifiable. |
| 8 | SDKs and deployment platform | `sdk/`, `infrastructure/`, historical workflows | Bound to an unvalidated standalone API and unverified cloud topology. | Archive only. Restore only after all reactivation gates pass. |
| 9 | Research and product documents | `docs/` and `docs/research/` | Market, competitor, compliance, and performance claims may be stale or unsupported. | Treat as leads for fresh primary-source research, never as current evidence. |

## Migration Contract

Every extraction must:

1. Name the destination repository, owning module, consumer, and acceptance test before code moves.
2. Copy the smallest useful asset rather than importing the AgentGuard application or database model.
3. Preserve license and source provenance and remove secrets, customer data, and generated reports.
4. Add attack and benign fixtures, deterministic replay where applicable, and explicit false-positive or failure behavior.
5. For any LLM-backed path, prove redaction before egress, credential isolation, a no-egress mode, a hard spend limit, and deterministic timeout/provider-error behavior.
6. Run the destination repository's security, quality, and independent-review gates.
7. Record the source commit and destination commit so later fixes can be traced.

## Frozen and Archived Work

- `codex/p0-release-truth` is limited to archive security and truth-maintenance work. Local tests, builds, and any reviewed merge from that lane are repository evidence only; they do not reactivate the standalone product or authorize deployment, provider traffic, registration, or customer use.
- The historical standalone README contains unsupported product claims and is labeled reference-only.
- The historical workflow files are outside `.github/workflows/` and cannot execute as GitHub Actions in this repository.

## Reactivation Gates

All gates in `PROJECT_STATUS.json` are mandatory. At minimum, reactivation requires a named design partner, current differentiation evidence, a secure golden journey with exact review, and sustainable pilot economics. Restoring old deployments or workflows is not itself reactivation proof.
