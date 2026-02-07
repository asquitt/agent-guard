# AgentGuard - AI Agent Incident Response for Financial Services

## Quick Start
```bash
cd agentguard-backend && /usr/local/bin/docker compose up -d
cd agentguard-frontend && npm run dev
```

## Architecture

**LLM Proxy Pattern**: All customer LLM traffic routes through AgentGuard proxy for real-time detection.

### Backend: `agentguard-backend/backend/` (FastAPI + Celery + PostgreSQL + Redis)
```
app/
├── api/              # 7 routers (auth, proxy, incidents, detectors, alerts, dashboard, webhooks)
├── models/           # 12 SQLAlchemy models (ALL models live here)
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
| DB      | 5433      | 5432           |
| Redis   | 6381      | 6379           |
| Frontend| 3000      | 3000           |

Frontend dev proxy: `next.config.js` rewrites `/api/*` → `http://localhost:8002`

## Commands
```bash
/usr/local/bin/docker compose ps|logs api|logs worker|restart api
cd agentguard-backend/backend && alembic revision --autogenerate -m "desc" && alembic upgrade head
cd agentguard-backend/backend && python scripts/check_model_imports.py
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

Before ANY commit:
1. Type check: `pyright app/` (backend) or `npx tsc --noEmit` (frontend)
2. Pre-commit hooks run automatically
3. Functional verification: curl endpoints, check logs

## Debug
```bash
# Auth token (host port 8001)
curl -s 'http://localhost:8001/api/v1/auth/login' -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"password"}' | jq -r '.access_token'

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

## Decision Authority

**DO autonomously:** Fix bugs, lint, types, restart services, patch deps, add logging, clean dead code

**ASK first:** Architecture changes, new features, schema changes, major deps, remove features, security config changes
