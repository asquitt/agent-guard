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
├── models/           # 12 SQLAlchemy models
├── services/         # Core business logic
│   └── detection/    # Detection algorithms (hallucination, PII, compliance, cost)
├── tasks/            # Celery background tasks
├── core/             # Config, database, auth, deps
├── schemas/          # Pydantic request/response schemas
└── utils/            # Utilities
```

### Frontend: `agentguard-frontend/src/` (Next.js 14 + TypeScript)
```
app/                  # 8 pages max at MVP
components/           # layout/, ui/, dashboard/, incidents/
hooks/                # api/, useAuth
lib/                  # api/, providers
types/                # TypeScript definitions
```

## Commands
```bash
/usr/local/bin/docker compose ps|logs api|logs worker|restart api
cd agentguard-backend/backend && alembic revision --autogenerate -m "desc" && alembic upgrade head
cd agentguard-backend/backend && python scripts/check_model_imports.py
pre-commit run --all-files
```

## File Placement Rules (MANDATORY)

### Backend
| File Type | Location |
|-----------|----------|
| Model | `app/models/` (ALL models with `__tablename__`) |
| API router | `app/api/` |
| Detection algorithm | `app/services/detection/` |
| Background task | `app/tasks/` |
| Pydantic schema | `app/schemas/` |

### Frontend
| File Type | Location |
|-----------|----------|
| Page route | `src/app/(group)/feature/page.tsx` |
| Component | `src/components/{feature}/` |
| API client | `src/lib/api/` |
| Hook | `src/hooks/` or `src/hooks/api/` |
| Types | `src/types/` |

## Database Model Rules (CRITICAL)

ALL models with `__tablename__` MUST be in `app/models/`. For every new model:
1. Create file in `app/models/`
2. Import in `app/models/__init__.py` and add to `__all__`
3. Run `python scripts/check_model_imports.py`

**Alembic safety:** If autogenerate shows DROP TABLE, fix model imports first.

## Models (12 total)

| Model | Purpose |
|-------|---------|
| User | Authentication, organization membership |
| Organization | Multi-tenant isolation (replaces site_id) |
| ApiKey | API key management for proxy authentication |
| ProxyEndpoint | Configured LLM endpoints to intercept |
| ProxyRequest | Logged LLM API requests |
| Incident | Detected anomalies/violations |
| IncidentAction | Actions taken on incidents |
| Detector | Detection rule configurations |
| DetectorRule | Individual detection rules |
| Alert | Generated alerts |
| AlertDestination | Slack, PagerDuty, email configs |
| AuditLog | Compliance audit trail |

## Detection Categories

1. **Hallucination** - Factual inconsistency detection
2. **PII Leak** - Personal data exposure in outputs
3. **Compliance** - Regulatory violation detection (SOX, PCI-DSS, FFIEC)
4. **Cost Anomaly** - Unusual token consumption patterns
5. **Loop Detection** - Repeated outputs indicating agent stuck

## Key Patterns

### Backend API Pattern
```python
@router.get("/incidents")
async def list_incidents(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    # ALWAYS filter by org_id for tenant isolation
    return await incident_service.list_for_org(db, org.id)
```

### Frontend Query Pattern
```typescript
const { data: incidents } = useQuery({
    queryKey: ['incidents'],
    queryFn: () => incidentsApi.list(),
});
```

## Tenant Isolation (CRITICAL)

Every query on these tables MUST include `org_id` filter:
- incidents, proxy_requests, proxy_responses
- detectors, alerts, audit_logs

**Never** return data across organizations. This is a fintech product - compliance is non-negotiable.

## Tech Debt Prevention

- 800 line file limit (enforced by pre-commit)
- No `Any` types without justification
- No bare `except:` clauses
- All models in `app/models/` with proper `__init__.py` exports
- Split files at 400 lines (warning), enforce at 800 (block)

## Pre-commit Verification (MANDATORY)

Before ANY commit:
1. Type check: `pyright app/` (backend) or `npx tsc --noEmit` (frontend)
2. Pre-commit hooks run automatically
3. Functional verification: curl endpoints, check logs

## Debug
```bash
# Auth token
curl -s 'http://localhost:8000/api/v1/auth/login' -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"password"}' | jq -r '.access_token'

# Health check
curl http://localhost:8000/health

# Logs
/usr/local/bin/docker compose logs api --tail=100 -f
```

## Health
- db: 5432
- redis: 6379
- api: 8000
- worker: Celery (may show unhealthy initially - ok)

## Decision Authority

**DO autonomously:** Fix bugs, lint, types, restart services, run tests, patch deps, add logging

**ASK first:** Architecture changes, new features, schema changes, major deps, remove features

## Proactive Issue Resolution (MANDATORY)

When you discover ANY issue during investigation - fix it immediately:
- Bug in code → FIX IT
- Misconfiguration → FIX IT
- Dead code → CLEAN IT UP
- Missing mapping → ADD IT

**Do NOT** explain issues and move on. If you can identify it, you can fix it.

## Never Mark Tasks Complete Without Verification

- API responses: curl the endpoint
- Published content: verify URL returns 200
- Agent task completion: check actual result, not just status
- If you cannot verify, say so explicitly
