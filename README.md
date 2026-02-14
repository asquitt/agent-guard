# AgentGuard

AI agent security platform for financial services. The only platform that unifies **detection**, **containment**, and **response** for LLM-powered applications.

## What It Does

AgentGuard sits between your application and LLM providers as a transparent proxy. Every request and response is analyzed by 10 detection algorithms. When threats are detected, agents running in sandboxed environments are **immediately contained** — not just logged.

```
Your App  ──▶  AgentGuard Proxy  ──▶  LLM Provider
                    │                  (OpenAI, Anthropic,
                    ▼                   Gemini, Bedrock,
              Detection Engine          Azure OpenAI)
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   Incidents   Containment   Audit Log
       │            │
       ▼            ▼
    Alerts     Sandbox Kill
```

### Detect + Contain + Respond

No other platform combines all three. Sandbox platforms (E2B, Modal, Daytona) isolate code but have zero detection. Security platforms (Lakera, Arthur AI) detect but cannot stop execution. AgentGuard does both.

| Capability | E2B / Modal | Lakera / CalypsoAI | Arthur AI | **AgentGuard** |
|------------|-------------|-------------------|-----------|----------------|
| Detect threats | - | Yes | Yes | **Yes** |
| Contain agents | Yes | - | - | **Yes** |
| Incident response | - | - | Partial | **Yes** |
| Financial compliance | - | - | - | **Yes** |

## Detection Categories

| Category | Mode | Description |
|----------|------|-------------|
| PII Leak | Sync | Personal data exposure in LLM outputs |
| Prompt Injection | Sync | Direct/indirect injection and jailbreak attempts |
| Prompt Extraction | Sync | System prompt leakage detection |
| Compliance | Sync | SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, EU AI Act violations |
| Tool/Function Call | Sync | Function signature and parameter validation |
| MCP Security | Sync | Model Context Protocol threat detection |
| Hallucination | Async | Factual inconsistency with financial benchmarks |
| Cost Anomaly | Async | Unusual token consumption patterns |
| Loop Detection | Async | Repeated outputs indicating stuck agents |
| Toxicity | Async | Bias and harmful content detection |

**Sync** detectors run in-request and can block/redact before the response reaches your app. **Async** detectors run post-response via Celery for computationally expensive analysis.

## Features

- **LLM Proxy** — Drop-in replacement for OpenAI/Anthropic APIs with 6 provider backends
- **Real-time Detection** — 10 algorithms across sync and async pipelines
- **Sandboxed Execution** — Capability-based agent containment with resource limits, network policies, and ephemeral environments
- **Incident Management** — Track, triage, and resolve detected issues
- **Alerting** — Slack, PagerDuty, email, and webhook integrations
- **Agent Governance** — Agent registry, behavior policies, human-in-the-loop review queues
- **Compliance Automation** — Framework mapping, automated reports, immutable audit trail
- **Threat Intelligence** — Attack pattern feeds, adversarial red teaming (25 test prompts)
- **Shadow AI Discovery** — Detect unauthorized AI usage across your organization
- **Multi-turn Analysis** — Conversation-level tracking across agent sessions
- **SSO** — SAML 2.0 and OAuth2/OIDC for enterprise identity providers
- **SDKs** — Python (async) and Node.js client libraries
- **API Playground** — Built-in testing UI for proxy endpoints

## Sandboxed Execution Runtime

Run AI agents in isolated, capability-controlled environments. Every action is evaluated against an explicit permission model and logged to a tamper-evident audit trail.

```bash
# 1. Create a sandbox with capabilities and resource limits
curl -X POST http://localhost:8001/api/v1/sandboxes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "trading-assistant",
    "capabilities": [
      {"type": "network:http", "target": "api.openai.com"},
      {"type": "api:call", "target": "market-data-api"}
    ],
    "resource_limits": {
      "cpu_shares": 512,
      "memory_mb": 256,
      "max_tokens": 10000,
      "timeout_seconds": 300
    },
    "network_policy": {
      "allowed_hosts": ["api.openai.com"],
      "allowed_ports": [443],
      "deny_all_egress": true
    }
  }'

# 2. Start an execution
curl -X POST http://localhost:8001/api/v1/sandboxes/{id}/execute \
  -H "Authorization: Bearer $TOKEN"

# 3. View audit log (every action logged with hash chain)
curl http://localhost:8001/api/v1/sandboxes/executions/{exec_id}/audit \
  -H "Authorization: Bearer $TOKEN"
```

**Key capabilities:**
- **Default-deny permissions** — Agents can only access files, APIs, and network endpoints explicitly granted
- **Resource enforcement** — CPU, memory, token budget, and timeout limits enforced in real-time
- **Network isolation** — Whitelist-only egress with per-host/port policies
- **Detection integration** — BLOCK detections automatically terminate sandbox executions
- **Hash-chained audit** — Every action logged with SHA-256 chain for tamper detection

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### 1. Start Backend

```bash
cd agentguard-backend
docker compose up -d
```

Wait for healthy: `curl http://localhost:8001/health`

### 2. Start Frontend

```bash
cd agentguard-frontend
npm install
npm run dev
```

### 3. Access

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8001 |
| API Docs (dev) | http://localhost:8001/docs |

### 4. Create an Account

```bash
curl http://localhost:8001/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"YourPassword1!","full_name":"Your Name","org_name":"Your Org"}'
```

### 5. Send Your First Proxied Request

```bash
# Create an API key in the dashboard, then:
curl http://localhost:8001/api/v1/proxy/v1/chat/completions \
  -H "Authorization: Bearer ag_live_<your_key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"Hello"}]}'
```

## Architecture

### Backend — FastAPI + Celery + PostgreSQL + Redis

```
agentguard-backend/backend/app/
├── api/              # 27 API routers (includes sandboxes)
├── models/           # 23 SQLAlchemy models (includes sandbox runtime)
├── services/         # Business logic
│   ├── detection/    # 10 detection algorithms + registry
│   ├── sandbox/      # Sandboxed execution runtime (7 modules)
│   └── providers/    # 6 LLM provider adapters
├── tasks/            # Celery background jobs (includes sandbox monitoring)
├── core/             # Config, auth, security middleware
├── schemas/          # Pydantic request/response models
└── utils/            # Utilities
```

### Frontend — Next.js 14 + TypeScript + TanStack Query

```
agentguard-frontend/src/
├── app/              # 29 routes (Next.js App Router)
├── components/       # Layout, UI, dashboard, incidents
├── hooks/            # TanStack Query hooks, auth, WebSocket
├── lib/              # API clients, constants, providers
└── types/            # TypeScript interfaces
```

### Services

| Service | Host Port | Container Port |
|---------|-----------|----------------|
| API (FastAPI) | 8001 | 8000 |
| PostgreSQL | 5433 | 5432 |
| Redis | 6381 | 6379 |
| Celery Worker | — | — |
| Celery Beat | — | — |
| Frontend (Next.js) | 3000 | 3000 |

## SDKs

### Python

```python
from agentguard import AgentGuardClient

client = AgentGuardClient(api_key="ag_live_...")
response = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Node.js

```typescript
import { AgentGuard } from 'agentguard';

const client = new AgentGuard({ apiKey: 'ag_live_...' });
const response = await client.chat.completions.create({
  model: 'gpt-4',
  messages: [{ role: 'user', content: 'Hello' }],
});
```

## Development

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

Hooks run automatically on commit: black, isort, flake8, pyright, file size limits, private key detection.

### Database Migrations

```bash
cd agentguard-backend/backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Running Tests

```bash
# Backend (targeted — don't run full suite)
cd agentguard-backend/backend
pytest tests/test_detectors.py -v

# Frontend
cd agentguard-frontend
npm run test
```

### Load Testing

```bash
cd load-tests
pip install -r requirements.txt
locust -f locustfile.py --host=http://localhost:8001 --headless -u 10 -r 2 -t 60s
```

### Security Audit

```bash
cd security-audit
pip install -r requirements.txt
./run_audit.sh
# Report: security-audit/reports/audit-report-YYYY-MM-DD.md
```

## Security

- **Tenant isolation** — Every query filtered by `org_id`. No cross-organization data leakage.
- **Encryption** — AES-256-GCM field-level encryption, HMAC-SHA256 API key hashing, bcrypt passwords
- **Auth hardening** — Account lockout (10 attempts/30 min), JWT token versioning, rate-limited auth endpoints
- **Security headers** — CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Permissions-Policy
- **Non-root container** — API runs as unprivileged user
- **Audit trail** — Immutable, hash-chained audit logging for all admin actions
- **Pre-commit scanning** — Private key detection, type checking, linting

## Documentation

| Document | Description |
|----------|-------------|
| [API Reference](docs/api-reference.md) | OpenAPI endpoint documentation |
| [Integration Guide](docs/integration-guide.md) | SDK usage and proxy setup |
| [Quick Start](docs/quickstart.md) | Getting started guide |
| [Production Plan](docs/PRODUCTION_PLAN.md) | AWS/Kubernetes deployment strategy |
| [Launch Checklist](docs/launch-checklist.md) | Pre-release validation |
| [Runbook](docs/runbook.md) | Operational procedures |
| [Enhancements](docs/ENHANCEMENTS.md) | Feature roadmap (39/39 complete) |

## License

Proprietary - All rights reserved.
