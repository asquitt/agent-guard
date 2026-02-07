---
paths:
  - agentguard-backend/backend/app/**
---

# Security Conventions (Backend)

## Tenant Isolation
- Every database query on multi-tenant tables MUST filter by `org_id`
- Multi-tenant tables: incidents, proxy_requests, detectors, detector_rules, alerts, alert_destinations, audit_logs, webhooks, api_keys
- Use `get_current_org` dependency to obtain the authenticated org
- Never pass org_id from client input — always derive from JWT

## Secrets
- Never log raw API keys or tokens — mask to first 8 characters
- Never hardcode credentials — use `settings.*` or environment variables
- Never include secrets in error responses

## SQL Safety
- Never use f-strings for SQL — use SQLAlchemy ORM or parameterized queries
- All filtering through SQLAlchemy `.where()` / `.filter()` clauses

## Input Validation
- All API inputs validated through Pydantic schemas
- Never trust path parameters without ownership verification
- Validate UUIDs before database lookup

## Output Sanitization
- Never expose internal error details to clients (use generic messages)
- Strip PII from log messages
- Detection metadata stored in DB only, not logged in plaintext
