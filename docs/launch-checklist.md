# AgentGuard Launch Checklist

## Pre-Launch (Code Complete)

- [ ] All Phase 1-8 sessions marked complete
- [ ] Backend: 66 tests passing
- [ ] Frontend: 19 tests passing
- [ ] CI/CD: All workflows configured (lint, test, build, deploy)
- [ ] No critical dependency vulnerabilities (`pip-audit`, `npm audit`)
- [ ] Pre-commit hooks passing on all files
- [ ] No TODO/FIXME items blocking launch

---

## Infrastructure (Before First Deploy)

### AWS Foundation
- [ ] AWS account configured with IAM roles (least-privilege)
- [ ] `terraform init && terraform plan` succeeds for all modules
- [ ] `terraform apply` creates all resources without errors
- [ ] VPC with multi-AZ subnets provisioned
- [ ] EKS cluster running and kubectl configured

### Container Registry
- [ ] ECR repos created (api, worker, frontend)
- [ ] Docker images built and pushed for all services
- [ ] Image scanning enabled on ECR repos

### Secrets & Configuration
- [ ] Secrets Manager populated:
  - [ ] Database credentials
  - [ ] Redis auth token
  - [ ] Application secret key
  - [ ] JWT signing key
  - [ ] Stripe API key + webhook secret
  - [ ] Sentry DSN
  - [ ] Detection LLM API key
- [ ] ExternalSecrets operator syncing to k8s secrets

### DNS & TLS
- [ ] Route 53 DNS configured for agentguard.app
- [ ] ACM certificate issued and validated
- [ ] Certificate attached to ALB
- [ ] HTTPS enforced (HTTP redirects to HTTPS)

### Security
- [ ] WAF rules active (SQL injection, XSS, rate limiting)
- [ ] Security groups restrict DB/Redis to VPC only
- [ ] RDS encryption at rest enabled
- [ ] Redis encryption in transit enabled

---

## First Deploy (Staging)

### Deployment
- [ ] `helm install` succeeds in staging namespace
- [ ] All pods healthy: API, Worker, Beat, Frontend
- [ ] No crash loops or restarts in first 5 minutes

### Health Checks
- [ ] `/health` returns 200
- [ ] `/health/ready` returns 200 (DB + Redis connected)
- [ ] Frontend loads at staging.agentguard.app

### Core Functionality
- [ ] Login/register flow works end-to-end
- [ ] JWT token refresh works
- [ ] Account lockout triggers after failed attempts
- [ ] LLM proxy forwards requests correctly
- [ ] Proxy responses include detection metadata
- [ ] Incidents created from detected issues
- [ ] Dashboard displays real-time data
- [ ] WebSocket connection delivers live updates

### Detection Pipeline
- [ ] Hallucination detector triggers on test input
- [ ] PII leak detector catches personal data
- [ ] Compliance detector flags regulatory violations
- [ ] Cost anomaly detector fires on high token usage
- [ ] Loop detection identifies repeated outputs

### Billing
- [ ] Stripe products and prices created (Starter, Pro, Enterprise)
- [ ] Webhook endpoint registered in Stripe dashboard
- [ ] Billing flow tested with Stripe test cards
- [ ] Usage metering records proxy requests correctly
- [ ] Plan limits enforced (request caps per tier)

---

## Monitoring

- [ ] Sentry DSN configured for backend
- [ ] Sentry DSN configured for frontend
- [ ] PrometheusRule alerts created:
  - [ ] API error rate > 1%
  - [ ] API p99 latency > 5s
  - [ ] Worker queue depth > 1000
  - [ ] Pod restart count > 5 in 10m
  - [ ] DB connection usage > 90%
- [ ] CloudWatch Logs receiving structured JSON logs
- [ ] Health check probes active in k8s (liveness + readiness)
- [ ] Alerting channel configured (PagerDuty / Slack / email)

---

## Security

### Transport
- [ ] CORS restricted to production domains only
- [ ] CSP headers active and tested
- [ ] HSTS enabled with appropriate max-age
- [ ] TLS 1.2+ enforced

### Authentication
- [ ] API keys use HMAC-SHA256 hashing (not stored in plaintext)
- [ ] Account lockout working after N failed attempts
- [ ] Token versioning active (revoke all sessions on password change)
- [ ] JWT expiry set appropriately (access: 15m, refresh: 7d)

### Application
- [ ] WAF blocking common attack patterns
- [ ] Rate limiting active on auth endpoints
- [ ] Tenant isolation verified (no cross-org data leaks)
- [ ] Input validation on all API endpoints via Pydantic
- [ ] No secrets in logs or error responses

### Compliance
- [ ] PII redacted from all log output
- [ ] Audit log capturing all admin actions
- [ ] Data retention policy documented

---

## Business

### Billing & Payments
- [ ] Stripe products and prices created:
  - [ ] Starter tier
  - [ ] Pro tier
  - [ ] Enterprise tier
- [ ] Webhook endpoint registered and verified in Stripe
- [ ] Billing flow tested end-to-end with test cards
- [ ] Invoice generation working

### Customer Support
- [ ] Support email configured (support@agentguard.app)
- [ ] Support workflow documented

### Legal
- [ ] Privacy policy page published
- [ ] Terms of service page published
- [ ] Cookie policy (if applicable)
- [ ] DPA template available for enterprise customers

### Documentation
- [ ] API reference published
- [ ] Integration guide published
- [ ] Quickstart guide published

---

## Post-Launch

### Production Promotion
- [ ] Staging fully tested and signed off
- [ ] Promote staging configuration to production
- [ ] Production smoke test passes:
  - [ ] `/health` returns 200
  - [ ] `/health/ready` returns 200
  - [ ] Login works
  - [ ] Proxy request processed
  - [ ] Incident created from detection
  - [ ] Dashboard loads with data

### Operations
- [ ] On-call rotation established
- [ ] Runbook reviewed by on-call team
- [ ] Rollback procedure tested
- [ ] Backup and restore procedure tested

### First Customer
- [ ] First real customer onboarded
- [ ] Customer successfully sending proxy traffic
- [ ] Detections firing correctly on real data
- [ ] Customer dashboard showing accurate metrics
- [ ] Billing recording usage correctly

---

## Sign-Off

| Milestone | Owner | Date | Status |
|-----------|-------|------|--------|
| Code complete | | | |
| Infrastructure ready | | | |
| Staging deployed | | | |
| Security review passed | | | |
| Monitoring confirmed | | | |
| Production deployed | | | |
| First customer live | | | |
