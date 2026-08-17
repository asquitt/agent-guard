---
name: project-quality
description: Enforce AgentGuard's autonomous delivery, verification, and exact-review standard for non-trivial implementation, bug-fix, security, persistence, UI, and release work.
---

# AgentGuard Project Quality

Use this workflow for any non-trivial change. Read `AGENTS.md`, `CLAUDE.md`, and the closest scoped instructions before editing.

## Execute

1. Inspect `git status -sb` and preserve unrelated work.
2. State assumptions, scope, and measurable success criteria.
3. Search models, API routers, detection services, Celery tasks, hooks, components, and registries before creating a new concern home.
4. Reproduce bugs or contract gaps with the narrowest useful test.
5. Implement the smallest complete fix and update every touched caller, export, registry, migration, and contract.

## Verify

Run focused backend pytest and Pyright under `agentguard-backend/backend`; frontend lint, typecheck, unit tests, and build under `agentguard-frontend`; then direct API, worker, WebSocket, or browser proof when those boundaries changed.

Do not infer success from a status flag, HTTP 200, mock, or healthy container alone. Inspect the produced incident or detection result, `org_id` ownership, persistence, alert/task consumers, and the customer-visible dashboard state. Exercise negative authorization and failure or recovery cases whenever those boundaries changed.

## Review and handoff

Material production, security, isolation, autonomous-mutation, persistence, provider-routing, or public-UI changes require the independent exact-commit review in `.github/ai-review/senior-review.md`. HIGH or MEDIUM findings block merge or deployment.

Report exact branch and head, tests and probes run, runtime or public evidence, review status, rollback and cleanup state, and anything still unverified. Never fabricate evidence.
