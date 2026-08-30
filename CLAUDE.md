# AgentGuard - AI Agent Incident Response for Financial Services

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

### Commit cadence and pull-request lifecycle

- One branch and one pull request represent one coherent customer-impact or operational slice. Start material work from the latest verified default branch on `codex/<short-slug>` unless the task already owns a suitable branch.
- Commit each verified, bisectable checkpoint and at least once at the end of a successful work session. Do not wait for a large dump, create noisy save-point commits, or mix unrelated cleanup.
- Every commit must preserve focused green evidence for its changed property. Use conventional messages, stage only task-owned files, and never add AI co-author trailers.
- Batch local commits and push once at the authorized session or correction-cycle boundary. Do not push after every commit, force-push, amend, rebase, or otherwise rewrite a candidate that has been shared or reviewed.
- At the first authorized push for a material slice, open or update one draft pull request; never create a duplicate PR for the same branch. Documentation that accompanies code stays in that PR. Do not create a PR solely for low-risk documentation unless repository protection requires it.
- Keep the PR draft while required tests, preview or runtime proof, rollback planning, cleanup, or independent exact-commit review remains incomplete. Record exact base, head, and tree SHAs plus the commands and results that support the candidate.
- Freeze the PR head for independent review. HIGH or MEDIUM findings keep it blocked and draft; make the smallest coherent fix as a new commit, push once, freeze the new head, rerun affected gates, and request bounded re-review.
- Mark ready and merge only when the current remote head is the reviewed head, required evidence is green, conversations are resolved, and the task includes merge or release authority. Use a merge commit, not squash or rebase, so candidate commits and review identities remain recoverable.
- An accepted PR is merged and GitHub closes it automatically. Manually close only an abandoned, duplicate, or explicitly superseded PR, and leave a final comment naming the reason, preserved head SHA, remaining blockers, and successor when one exists. Never close a PR to hide a blocker.
- After merge, record the PR number and merge SHA, verify the merged tree and any required deployment or public behavior, then report rollback and cleanup state. Delete a branch or worktree only when it is merged or superseded, clean, idle, and explicitly released; otherwise preserve it.

### Handoff

Report the exact branch and head, files changed, tests and probes run, runtime or public evidence, independent-review result, rollback and cleanup state, and remaining risks. Distinguish complete, partial, blocked, and unverified work explicitly.

### AgentGuard risk focus

Prioritize tenant isolation, proxy and detector coverage, PII or secret redaction, async API versus sync Celery behavior, and authenticated WebSocket delivery.

## Quick Start
```bash
/usr/local/bin/docker compose up -d
cd agentguard-frontend && npm run dev
```

## Architecture

**LLM Proxy Pattern**: All customer LLM traffic routes through AgentGuard proxy for real-time detection.

### Backend: `agentguard-backend/backend/` (FastAPI + Celery + PostgreSQL + Redis)
```
app/
├── api/              # FastAPI routers
├── models/           # SQLAlchemy models (ALL models live here)
├── services/         # Business logic
│   └── detection/    # Detection algorithms + shared types (types.py, registry.py)
├── tasks/            # Celery tasks (analysis, alerting, billing)
├── core/             # Config, database, auth, deps
├── schemas/          # Pydantic request/response schemas
└── utils/            # Utilities
```

### Frontend: `agentguard-frontend/src/` (Next.js 14 + TypeScript)
```
app/                  # Pages (Next.js App Router)
components/           # layout/, ui/, dashboard/, incidents/
hooks/                # api/, useAuth, useWebSocket
lib/                  # api/, providers, constants.ts
types/                # TypeScript definitions
```

## Ports (Host → Container)
| Service | Host Port | Container Port |
|---------|-----------|----------------|
| API     | 8001      | 8000           |
| DB      | 5434      | 5432           |
| Redis   | 6381      | 6379           |
| Frontend| 3000      | 3000           |

Frontend dev proxy: `next.config.js` rewrites `/api/*` → `http://localhost:8001`

## Commands
```bash
/usr/local/bin/docker compose ps|logs api|logs worker|restart api
cd agentguard-backend/backend && python -m pytest <target> -q
cd agentguard-backend/backend && python -m pyright app
cd agentguard-backend/backend && alembic revision --autogenerate -m "desc" && alembic upgrade head
cd agentguard-backend/backend && python scripts/check_model_imports.py
cd agentguard-frontend && npm run type-check && npm test && npm run build
pre-commit run --all-files
```

## File Placement (MANDATORY)

### Backend
| Type | Location |
|------|----------|
| Model (with `__tablename__`) | `app/models/` |
| API router | `app/api/` |
| Detection algorithm | `app/services/detection/` |
| Background task | `app/tasks/` |
| Pydantic schema | `app/schemas/` |
| Shared detection types | `app/services/detection/types.py` |

### Frontend
| Type | Location |
|------|----------|
| Page route | `src/app/(group)/feature/page.tsx` |
| Component | `src/components/{feature}/` |
| API client | `src/lib/api/` |
| Hook | `src/hooks/` or `src/hooks/api/` |
| Types | `src/types/` |
| Shared constants | `src/lib/constants.ts` |

## Database Model Rules (CRITICAL)

ALL models with `__tablename__` MUST be in `app/models/`. For every new model:
1. Create file in `app/models/`
2. Import in `app/models/__init__.py` and add to `__all__`
3. Run `python scripts/check_model_imports.py`

**Alembic safety:** If autogenerate shows DROP TABLE, fix model imports first.

## Security (CRITICAL)

### Tenant Isolation
Every query on these tables MUST include `org_id` filter:
- incidents, proxy_requests, detectors, alerts, audit_logs, webhooks

**Never** return data across organizations. This is a fintech product — compliance is non-negotiable.

### Secrets
- Never log raw API keys or tokens — mask to first 8 chars
- Never hardcode secrets — use `settings.SECRET_KEY`, env vars
- Never use f-string SQL — always use parameterized queries / ORM

### Input Validation
- All user input validated via Pydantic schemas at API boundary
- Never trust client-side authorization — verify `org_id` ownership server-side
- Sanitize before database writes; escape before rendering

### PII in Logs
- Redact email addresses, names, financial data in log output
- Detection results may contain PII — store in DB, never in plaintext logs

## Detection Categories

1. **Hallucination** — Factual inconsistency detection
2. **PII Leak** — Personal data exposure in outputs
3. **Compliance** — Regulatory violation detection (SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, EU-AI-ACT)
4. **Cost Anomaly** — Unusual token consumption patterns
5. **Loop Detection** — Repeated outputs indicating agent stuck
6. **Prompt Injection** — Direct/indirect injection, jailbreak, system extraction

Shared mapping: `ACTION_MODE_MAP` in `app/services/detection/types.py` (used by both sync pipeline and async Celery tasks).

## Key Patterns

### Backend: Async handlers + sync Celery tasks
```python
# FastAPI (async)
async def list_incidents(org: Organization = Depends(get_current_org), db: AsyncSession = Depends(get_db)):
    return await incident_service.list_for_org(db, org.id)  # ALWAYS filter by org_id

# Celery (sync) — uses SessionLocal(), NOT AsyncSessionLocal
```

### Frontend: TanStack Query + shared constants
```typescript
import { SEVERITY_COLORS, STATUS_COLORS } from '@/lib/constants';
const { data } = useQuery({ queryKey: ['incidents'], queryFn: () => listIncidents(filters) });
```

### WebSocket: Redis pub/sub
- Channel: `org:{org_id}:events`
- Auth: `?token=<jwt>` query param (browser WS can't send headers)
- Async client for FastAPI, sync client for Celery

## Dead Code Prevention

- No commented-out imports or stub functions
- No tasks in Celery beat that don't do real work
- Every function must have at least one caller
- Every export must have at least one importer
- Shared constants go in one place (backend: `detection/types.py`, frontend: `lib/constants.ts`)

## Tech Debt Prevention

- 800 line file limit (enforced by pre-commit hook)
- No `Any` types without justification
- No bare `except:` clauses — always specify exception type
- All models in `app/models/` with proper `__init__.py` exports

## Pre-commit Verification (MANDATORY)

Before any commit, run verification in proportion to the changed boundary:
1. Backend changes: focused pytest plus `pyright app/` under `agentguard-backend/backend`.
2. Frontend changes: focused tests plus lint, `npx tsc --noEmit`, and build under `agentguard-frontend`.
3. Product or runtime behavior changes: exercise the affected API, worker, WebSocket, or browser path and inspect its produced state and logs.
4. Policy, documentation, or hook-only changes: run focused syntax, schema, contract, and portability checks; record product-stack and runtime probes as not applicable with the reason.
5. Run configured pre-commit hooks for the files being committed.

## Debug
```bash
# Source TEST_EMAIL and TEST_PASSWORD from an approved local fixture without printing them.
jq -n --arg email "$TEST_EMAIL" --arg password "$TEST_PASSWORD" \
  '{email:$email,password:$password}' | \
  curl -s 'http://localhost:8001/api/v1/auth/login' -X POST \
  -H 'Content-Type: application/json' --data-binary @- | jq -r '.access_token'

# Health check
curl http://localhost:8001/health

# Logs
/usr/local/bin/docker compose logs api --tail=100 -f
```

## Enhancement Progress Tracking (MANDATORY)

When working on enhancements from `docs/ENHANCEMENTS.md`:
1. **Before starting**: Update the plan file (`.claude/plans/`) with current progress table
2. **After each enhancement**: Mark it DONE in the plan file with commit hash
3. **After committing**: Update `docs/ENHANCEMENTS.md` Status column (add `DONE` to completed rows)
4. **On context loss**: Read the plan file first to pick up where you left off

Current P0 status is tracked in the plan file and in the Month 1 table of `docs/ENHANCEMENTS.md`.

## NEVER Mark Tasks Complete Without Verification (CRITICAL)

**NEVER claim something is working or mark a task complete without ACTUALLY verifying it.**

### Verification Requirements
1. **API responses**: curl the endpoint, check the response
2. **Detection algorithms**: Test with sample payloads, verify detection triggers
3. **Security fixes**: Verify unauthorized access is rejected (401/403)
4. **Celery tasks**: Check logs, verify execution completed

### When Verification Fails
1. Diagnose the root cause
2. Fix the underlying issue
3. Re-run and verify again
4. Only then report success

**If you cannot verify, say so explicitly. Never fabricate verification results.**

## Workflow Conventions (MANDATORY)

### Immediate Execution, Not Summarization
When implementing from a plan document, start execution immediately. Do NOT summarize or ask which phase to start.

### Scope Discipline
Implement exactly what's requested before expanding. Do NOT over-scope.

### Debugging Structure
Start from the error traceback → trace the call chain → identify root cause → then fix.

### API Contract-First Development
Before implementing features spanning backend and frontend:
1. Define the Pydantic response model in backend
2. Create the corresponding TypeScript interface in frontend
3. Verify field names, types, and nullability match
4. THEN implement

## Mandatory Architectural Review (BEFORE IMPLEMENTATION)

When a task involves creating 2+ new files or modifying 3+ existing files:
1. **File Size**: Will any file exceed 800 lines?
2. **Tenant Isolation**: Does every query filter by `org_id`?
3. **Security**: Are auth guards and rate limits in place?
4. **Dead Code Prevention**: Are all imports/exports updated?

Use subagents only for genuinely independent work or when the user or applicable instructions request parallelism.

## Decision Authority

**DO autonomously:** Make scoped fixes, run focused tests and quality gates, restart local services when needed, add task-relevant diagnostics, and remove dead code created by the current change

**ASK first:** Architecture changes, new features, schema changes, major deps, remove features, security config changes
