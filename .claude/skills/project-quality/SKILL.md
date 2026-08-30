---
name: project-quality
description: Enforce AgentGuard's autonomous delivery, verification, and exact-review standard for non-trivial implementation, bug-fix, security, persistence, UI, and release work.
---

# AgentGuard Project Quality

Use this workflow for any non-trivial change. Read `AGENTS.md`, `CLAUDE.md`, and the closest scoped instructions before editing.

## Execute

1. Inspect `git status -sb` and preserve unrelated work.
2. State assumptions, scope, and measurable success criteria.
3. Search existing models, routers, detection services, tasks, hooks, components, and registries before adding a new concern home.
4. Reproduce bugs or contract gaps with the narrowest useful test.
5. Implement the smallest complete fix and update every touched caller, export, registry, migration, and API contract.

## Verify

Run focused tests first, then the changed-stack gates. For AgentGuard this normally means backend tests and Pyright under `agentguard-backend/backend`, frontend lint/typecheck/tests/build under `agentguard-frontend`, plus direct API, worker, WebSocket, or browser proof when those boundaries changed.

Do not infer success from a status flag, HTTP 200, mocked detector, or container health alone. Inspect the produced incident/detection result, organization ownership, persistence, downstream consumer, and customer-visible state. Exercise unauthorized and cross-organization cases for protected data.

## Review and handoff

Material production, security, tenant-isolation, autonomous-mutation, persistence, provider-routing, or public-UI changes require the independent exact-commit review in `.github/ai-review/senior-review.md`. HIGH or MEDIUM findings block merge or deployment.

Report exact branch/head, tests and probes run, runtime/public evidence, review status, rollback/cleanup state, and anything still unverified. Never fabricate evidence.
