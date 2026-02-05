# AgentGuard

AI Agent Incident Response Platform for Financial Services.

## Overview

AgentGuard provides real-time detection and response for AI agent failures in financial services environments. It acts as an LLM proxy, intercepting all AI traffic to detect hallucinations, PII leaks, compliance violations, and other anomalies.

## Features

- **LLM Proxy**: Intercept and monitor all LLM API calls
- **Real-time Detection**: Identify hallucinations, PII leaks, compliance violations
- **Incident Management**: Track and manage detected issues
- **Alerting**: Integrate with Slack, PagerDuty, email, webhooks
- **Compliance**: Built for SOX, PCI-DSS, FFIEC requirements
- **Audit Trail**: Complete logging for regulatory compliance

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### Development Setup

```bash
# Start backend services
docker compose up -d

# Install frontend dependencies
cd agentguard-frontend
npm install
npm run dev
```

### Access

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Your App   │────▶│  AgentGuard  │────▶│  LLM APIs   │
│             │◀────│    Proxy     │◀────│ (OpenAI,    │
└─────────────┘     └──────────────┘     │  Anthropic) │
                           │             └─────────────┘
                           ▼
                    ┌──────────────┐
                    │  Detection   │
                    │   Engine     │
                    └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │Incidents │ │  Alerts  │ │  Audit   │
        └──────────┘ └──────────┘ └──────────┘
```

## Tech Stack

### Backend
- FastAPI (Python 3.11)
- PostgreSQL 15
- Redis 7
- Celery (background tasks)
- SQLAlchemy 2.0

### Frontend
- Next.js 14
- TypeScript
- TanStack Query
- Tailwind CSS

## Development

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# Backend
cd agentguard-backend/backend
pytest

# Frontend
cd agentguard-frontend
npm run test
```

### Database Migrations

```bash
cd agentguard-backend/backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## License

Proprietary - All rights reserved.
