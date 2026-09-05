# Archived AgentGuard On-Call Operations Runbook

> **Mothballed planning artifact:** AgentGuard has no authorized standalone
> deployment. This runbook describes a historical target Kubernetes/AWS model;
> it is not evidence that its services, alerts, domains, or escalation paths
> exist. Do not run these commands or incur runtime/provider spend unless an
> explicit reactivation decision satisfies every gate in
> [`PROJECT_STATUS.json`](../PROJECT_STATUS.json), then resolve and verify the
> exact target first.

## Service Architecture Quick Reference

| Service | Type | Port | Health Check | Notes |
|---------|------|------|-------------|-------|
| API | FastAPI | 8000 | `/health`, `/health/ready` | Stateless, HPA-scaled |
| Worker | Celery | None (pulls from queue) | Celery inspect ping | No inbound ports |
| Beat | Celery scheduler | None | Single instance | Recreate strategy (no duplicates) |
| Frontend | Next.js | 3000 | `/` returns 200 | Static + SSR |
| Database | PostgreSQL 15 | 5432 | RDS health | Multi-AZ in production |
| Cache/Queue | Redis 7 | 6379 | `redis-cli ping` | ElastiCache cluster |

---

## Common Incidents & Responses

### 1. API Pod Crash-looping

**Symptoms:** `CrashLoopBackOff` status, 503 responses from ALB.

**Diagnosis:**
```bash
kubectl logs <pod> -n agentguard --previous
kubectl describe pod <pod> -n agentguard
```

**Common Causes:**
- **DB connection exhaustion** -- Check RDS connection count in CloudWatch.
- **OOM killed** -- Check `kubectl describe pod` for `OOMKilled` reason. Increase memory limits.
- **Config error** -- Missing env var or secret. Check `kubectl get externalsecrets -n agentguard`.

**Fix:**
1. Check `/health/ready` to isolate DB vs Redis failure.
2. Verify RDS and Redis connectivity from inside the pod:
   ```bash
   kubectl exec -it <pod> -n agentguard -- python -c "from app.core.database import engine; print('DB OK')"
   ```
3. If OOM, increase resource limits in Helm values and redeploy.
4. If config error, fix the ExternalSecret or ConfigMap and restart.

---

### 2. High API Error Rate (>1%)

**Symptoms:** Sentry alert fires, elevated 5xx in ALB metrics.

**Diagnosis:**
```bash
# Check Sentry for error grouping and stack traces

# Recent API logs
kubectl logs deployment/agentguard-api -n agentguard --tail=200 | grep ERROR

# RDS metrics
# Check CloudWatch: CPUUtilization, DatabaseConnections, ReadLatency

# Redis metrics
# Check CloudWatch: EngineCPUUtilization, DatabaseMemoryUsagePercentage
```

**Common Causes:**
- **Slow DB queries** -- Check RDS Performance Insights for top SQL.
- **Upstream LLM timeout** -- Detection LLM or customer proxy target unreachable.
- **Memory pressure** -- Redis evicting keys.

**Fix:**
1. If DB-related: identify slow queries, add missing indexes, or scale RDS.
2. If LLM-related: check rate limits (see incident #5).
3. If widespread across all endpoints: rollback to last known good release.

**Escalation:** If error rate exceeds 5% for more than 5 minutes, page the on-call lead.

---

### 3. Worker Queue Backlog (>1000 tasks)

**Symptoms:** Delayed incident creation, stale dashboard data, Prometheus alert fires.

**Diagnosis:**
```bash
# Check HPA status
kubectl get hpa -n agentguard

# Check current worker count
kubectl get pods -n agentguard -l app=agentguard-worker

# Check queue depth (exec into any pod with Redis access)
kubectl exec deployment/agentguard-api -n agentguard -- \
  python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.llen('celery'))"
```

**Fix:**
```bash
# Scale workers manually if HPA is at max
kubectl scale deployment/agentguard-worker --replicas=6 -n agentguard
```

**Root Causes:**
- Spike in proxy traffic generating many detection tasks.
- Slow detection LLM increasing per-task duration.
- Worker pods stuck on long-running tasks (check for timeouts).

**Prevention:** Adjust HPA `maxReplicas` if spikes are recurring.

---

### 4. Database Connection Exhaustion

**Symptoms:** 503 from `/health/ready`, `connection pool exhausted` or `too many connections` in logs.

**Diagnosis:**
```bash
# Check current connections
# CloudWatch: RDS DatabaseConnections metric

# Check API logs for connection errors
kubectl logs deployment/agentguard-api -n agentguard --tail=100 | grep -i "connection"
```

**Fix (immediate):**
```bash
# Restart API pods to reset connection pools
kubectl rollout restart deployment/agentguard-api -n agentguard
```

**Fix (root cause):**
- Check for connection leaks: sessions not being closed properly.
- Increase pool size in `DATABASE_URL` params: `?pool_size=20&max_overflow=10`.
- Scale down API replicas if total connections exceed RDS `max_connections`.

**Formula:** Total connections = `api_replicas * (pool_size + max_overflow)`. Must be less than RDS `max_connections` (default ~400 for db.r6g.large).

---

### 5. Detection LLM Rate Limited

**Symptoms:** Hallucination and compliance detectors silently returning `detected=False`. No errors raised, but detection quality drops.

**Diagnosis:**
```bash
# Check for rate limit messages
kubectl logs deployment/agentguard-worker -n agentguard --tail=200 | grep -i "rate.limit"
```

**Fix:**
1. Increase `DETECTION_LLM_RPM` environment variable.
2. Switch to a faster or higher-quota model in `DETECTION_LLM_MODEL`.
3. Add exponential backoff if not already present.

**Note:** Rate limiting does NOT raise exceptions by default. Detectors fail open (return `detected=False`) to avoid blocking proxy requests. Monitor detection rates in the dashboard for anomalies.

---

### 6. Stripe Webhook Failures

**Symptoms:** Billing events not processing, customers not getting plan upgrades.

**Diagnosis:**
1. Check Stripe dashboard: Developers -> Webhooks -> Recent events.
2. Look for HTTP status codes on failed deliveries.
3. Check API logs for webhook handler errors:
   ```bash
   kubectl logs deployment/agentguard-api -n agentguard --tail=100 | grep -i "webhook"
   ```

**Fix:**
1. **Signature mismatch:** Verify `STRIPE_WEBHOOK_SECRET` matches the secret in Stripe dashboard.
2. **Endpoint unreachable:** Check ALB and ingress configuration.
3. **Handler error:** Fix the bug, deploy, then replay failed events from Stripe dashboard.

**Replay:**
Stripe dashboard -> Webhooks -> Select endpoint -> Failed events -> Resend.

---

## Rollback Procedure

```bash
# List recent Helm releases
helm history agentguard -n agentguard

# Rollback to previous revision
helm rollback agentguard <revision> -n agentguard --wait

# If DB migration needs rollback
kubectl run rollback-migration --image=<api-image> --restart=Never -n agentguard \
  --command -- alembic downgrade -1

# Verify rollback succeeded
kubectl get pods -n agentguard
curl -s "${AGENTGUARD_BASE_URL:?set the deployment origin}/health" | jq .
```

**Important:** Always rollback the Helm release first, then handle DB migrations separately. Never rollback a migration without rolling back the application code that depends on it.

---

## Scaling Commands

```bash
# Manual scale API
kubectl scale deployment/agentguard-api --replicas=5 -n agentguard

# Manual scale workers
kubectl scale deployment/agentguard-worker --replicas=6 -n agentguard

# Check HPA status
kubectl get hpa -n agentguard

# Check pod resource usage
kubectl top pods -n agentguard

# Check node capacity
kubectl top nodes
```

---

## Useful Commands

```bash
# Pod status
kubectl get pods -n agentguard

# Recent API logs
kubectl logs deployment/agentguard-api -n agentguard --tail=100

# Recent worker logs
kubectl logs deployment/agentguard-worker -n agentguard --tail=100

# Follow logs in real time
kubectl logs deployment/agentguard-api -n agentguard -f

# Exec into pod for debugging
kubectl exec -it deployment/agentguard-api -n agentguard -- /bin/bash

# Check external secrets sync status
kubectl get externalsecrets -n agentguard

# Database migration status
kubectl exec deployment/agentguard-api -n agentguard -- alembic current

# Database migration history
kubectl exec deployment/agentguard-api -n agentguard -- alembic history --verbose

# Redis connectivity check
kubectl exec deployment/agentguard-api -n agentguard -- \
  python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"

# Force restart all services
kubectl rollout restart deployment -n agentguard
```

---

## Alerting Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| API error rate | >0.5% | >1% | Check Sentry, logs |
| API p99 latency | >2s | >5s | Check DB, LLM calls |
| Worker queue depth | >500 | >1000 | Scale workers |
| DB connections | >70% max | >90% max | Restart pods, increase pool |
| Redis memory | >70% | >85% | Check eviction policy |
| Pod restarts | >2 in 10m | >5 in 10m | Check crash reason |

---

## Contacts

| Role | Responsibility |
|------|---------------|
| On-call engineer | First responder for all alerts |
| Backend lead | Escalation for API/worker/DB issues |
| Infra lead | Escalation for AWS/k8s/Terraform issues |
| Security lead | Escalation for auth/WAF/compliance issues |
