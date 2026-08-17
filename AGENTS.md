# AgentGuard — Multi-Agent Workflow Guide

## Autonomous Delivery Standard

These rules govern implementation, diagnosis, review, release, and handoff. More specific project invariants below remain binding.

### Scope and planning

- State assumptions, scope, and measurable success criteria before multi-step work.
- Turn the plan into `step -> verification` pairs and keep it current.
- Proceed autonomously with routine, reversible work inside the requested scope.
- Stop for missing credentials, destructive or production-wide actions, ownership conflicts, or choices that materially change the product.
- A request to diagnose, review, or report is read-only unless the user also authorizes changes.
- Inspect `git status -sb` first. Preserve unrelated tracked, untracked, staged, and generated work.

### Simplicity and adoption

- Write the minimum code that completely solves the requested problem.
- Search callers, registries, shared services, adapters, hooks, and existing implementations before adding a new abstraction or concern home.
- Extend the canonical layer when responsibility is the same. If a shared layer changes, migrate the touched callers rather than creating a sibling implementation.
- Do not add speculative configuration, redundant fallback paths, or infrastructure for remote hypotheticals.
- Update affected imports, exports, routers, task maps, migrations, schemas, clients, and documentation.
- Remove only dead code made obsolete by the current change. Do not clean unrelated debt.

### Outcome truth and no false greens

- A passing test, HTTP 200, status flag, database row, mock, screenshot, or healthy container is evidence, not proof of the claimed outcome.
- Verify the real producer, persistence, ownership boundary, consumer, and user or operator-visible result.
- For AgentGuard, a real organization-scoped request must flow through proxy or ingestion, detector execution, persisted incident or evidence, alert/task consumers, and the authenticated dashboard without leaking PII or another tenant's data.
- Mocks and deterministic fixtures are acceptable development evidence only. Label them clearly and do not use them to support live-provider or production claims.
- Deployment proof requires exact repository, revision, artifact or image, configuration contract, health behavior, and rendered application identity.
- Never weaken a customer-facing claim to make QA pass. Fix the behavior or request an explicit positioning decision.

### Verification

- Bug fix: reproduce with a focused regression, implement the smallest fix, and prove the regression now passes.
- Start with the narrowest relevant checks, then run changed-file gates and broader build, integration, E2E, security, or release gates in proportion to risk.
- The normal AgentGuard path is focused backend pytest and Pyright, frontend lint/typecheck/tests/build, then direct API, worker, WebSocket, and browser proof as applicable.
- Test negative and adversarial cases for auth, isolation, validation, retries, partial failure, rollback, and cleanup when those boundaries change.
- Verify APIs with actual requests and response bodies, UI with a real render and interaction, persistence with stored and reloaded state, and background work with produced results and logs.
- If a required gate cannot run, report exactly what passed, what failed, and what remains unverified.

### Independent senior review

- Material production behavior, security boundaries, autonomous mutations, persistence, provider routing, migrations, deployment controls, and public UI changes require one separate independent xhigh review of an immutable base-to-head commit.
- Give the reviewer the full base and head SHAs, user requirements, affected architecture, tests, and runtime context. The reviewer is read-only and follows `.github/ai-review/senior-review.md`.
- HIGH or MEDIUM findings require a plausible current trigger, concrete impact, reproducible evidence, an affected file and line, and the smallest sufficient fix.
- Freeze the candidate on any admitted blocker. Fix narrowly, rerun relevant gates, commit a new head, and request one bounded re-review from the same reviewer.
- LOW, speculative, unrelated, stylistic, and non-reproducible observations do not extend the cycle.
- CI, previews, and deployment checks are separate evidence and do not replace independent review.

### Git, secrets, and production safety

- Stage and commit only files belonging to the current task. Use conventional, coherent commits without AI co-author trailers.
- Push once at the requested or final handoff boundary. Never force-push, rewrite history, or change remotes unless explicitly requested.
- Never print, log, screenshot, commit, or place secrets in command arguments. Source only required variables from an approved local or external secret store.
- Production starts read-only: verify target, identity, health, logs, rollback, and cleanup path before mutation.
- Never run destructive database, provider, deployment, or filesystem operations against an unresolved or broad target.
- Do not claim deployment, rollback, cleanup, or public verification that was not directly observed.

### Handoff

Report the exact branch and head, files changed, tests and probes run, runtime or public evidence, independent-review result, rollback and cleanup state, and remaining risks. Distinguish complete, partial, blocked, and unverified work explicitly.

### AgentGuard risk focus

Prioritize tenant isolation, proxy and detector coverage, PII or secret redaction, async API versus sync Celery behavior, and authenticated WebSocket delivery.

## When to Use Sub-Agents

Use sub-agents for:
- **Parallel exploration**: searching backend + frontend simultaneously
- **Deep research**: codebase-wide audits that would bloat main context
- **Independent tasks**: lint checks, grep sweeps, file discovery

Do NOT use sub-agents for:
- Single file reads or targeted greps (use Glob/Grep directly)
- Tasks that depend on the previous step's output
- Simple edits where you already know the file

## Agent Specializations

### Backend Agent
- Scope: `agentguard-backend/backend/app/`
- Key files: `models/`, `api/`, `services/detection/`, `tasks/`, `schemas/`
- Verify with: `pyright app/` (type check), `curl` endpoints
- Pattern: async handlers, sync Celery tasks, org_id tenant isolation

### Frontend Agent
- Scope: `agentguard-frontend/src/`
- Key files: `app/`, `components/`, `hooks/`, `lib/`, `types/`
- Verify with: `npx tsc --noEmit`
- Pattern: TanStack Query, shared constants from `lib/constants.ts`

### Detection Agent
- Scope: `agentguard-backend/backend/app/services/detection/`
- Key files: `types.py` (shared types + ACTION_MODE_MAP), `registry.py`, `pipeline.py`
- Sync detectors run in-request; async detectors run via Celery
- All detectors must register in `registry.py`

### Security Audit Agent
- Check: org_id filters on all queries, no raw secrets in logs
- Check: no f-string SQL, no hardcoded credentials
- Check: Pydantic validation at API boundary
- Check: no dangerouslySetInnerHTML in frontend

## Coordination Rules

1. **One agent per domain**: don't split a single backend change across agents
2. **Share context upfront**: include file paths and line numbers in prompts
3. **Verify after merge**: after combining agent outputs, run type checks on both stacks
4. **Prefer haiku for exploration**: use sonnet/opus only for complex reasoning

## Model Selection

| Task | Model |
|------|-------|
| File search, grep, quick lookups | haiku |
| Standard coding, reviews | sonnet |
| Architecture, multi-file refactors | opus |
