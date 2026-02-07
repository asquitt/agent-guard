# AgentGuard Production Plan

**Goal:** Ship a world-class, self-serve SaaS AI agent incident response platform for financial services in 10 weeks.

**Solo founder + Claude Code. Every session ends with working, committed, pushed code.**

---

## Decision Summary

| Decision | Choice |
|----------|--------|
| Timeline | 8-12 weeks (targeting 10) |
| Users | Self-serve SaaS |
| Deployment | Cloud-hosted (AWS EKS) |
| LLM Providers | OpenAI + Anthropic |
| Auth | Full SSO (SAML/OIDC) |
| Billing | Stripe (subscription tiers + usage metering) |
| Detectors | All 5 (hallucination, PII, compliance, cost, loop) |
| Proxy Action | Customer-configurable per detector (monitor/warn/redact/block) |
| Detection LLM | Hybrid (rule-based for PII/cost/loop, LLM-powered for hallucination/compliance) |
| Compliance | Full fintech (SOC 2 + PCI-DSS awareness + FFIEC) |
| Dashboard | Full enterprise (analytics, team management, compliance, billing) |
| Real-time | WebSocket + SSE/polling fallback |
| Rate Limiting | AWS API Gateway + Redis (defense in depth) |
| Data Retention | Tiered (Hot 30d Postgres → Warm 1yr S3 → Cold 7yr Glacier) |
| Onboarding | Quick-start wizard + developer docs/SDK |
| Observability | Sentry + structured logging |
| Testing | Full stack (backend unit/integration + frontend component + E2E Playwright) |
| Cloud | AWS (EKS/Kubernetes) |
| Existing Infra | Nothing — starting from scratch |

---

## Phase 1: Foundation (Weeks 1-2)

**Goal:** All 12 database models, auth system, and core API structure working end-to-end.

### Session 1.1: Database Models & Migrations ✅
**Done when:** All 12 models created, relationships defined, initial migration runs, `docker compose up` creates all tables.

- [x] Implement all 12 SQLAlchemy models with proper relationships:
  - `User` (id, email, hashed_password, full_name, role, org_id, is_active, created_at, updated_at)
  - `Organization` (id, name, slug, plan_tier, stripe_customer_id, settings, created_at)
  - `ApiKey` (id, org_id, key_hash, prefix, name, scopes, is_active, last_used_at, expires_at)
  - `ProxyEndpoint` (id, org_id, name, provider, target_url, is_active, config, created_at)
  - `ProxyRequest` (id, org_id, endpoint_id, method, path, request_body, response_body, status_code, latency_ms, token_count_input, token_count_output, model, cost_usd, created_at)
  - `Incident` (id, org_id, request_id, detector_id, severity, category, title, description, status, action_taken, metadata, created_at, resolved_at)
  - `IncidentAction` (id, incident_id, user_id, action_type, details, created_at)
  - `Detector` (id, org_id, name, category, is_active, action_mode, config, created_at)
  - `DetectorRule` (id, detector_id, name, rule_type, parameters, is_active)
  - `Alert` (id, org_id, incident_id, destination_id, status, sent_at, error_message)
  - `AlertDestination` (id, org_id, type, name, config, is_active)
  - `AuditLog` (id, org_id, user_id, action, resource_type, resource_id, details, ip_address, created_at)
- [x] Add proper indexes (org_id on every tenant table, composite indexes for common queries)
- [x] Add `ActionMode` enum: `monitor`, `warn`, `redact`, `block`
- [x] Generate and run initial Alembic migration
- [x] Verify with `docker compose up` — all tables created, no errors

### Session 1.2: Authentication System ✅
**Done when:** Register, login, token refresh, and user profile endpoints work via curl.

- [x] Implement auth router (`/api/v1/auth/`)
  - `POST /register` — create user + organization
  - `POST /login` — email/password → JWT access + refresh tokens
  - `POST /refresh` — refresh token rotation
  - `GET /me` — current user profile
  - `POST /logout` — invalidate refresh token
- [x] Implement password hashing (bcrypt via passlib)
- [x] JWT access tokens (30 min) + refresh tokens (7 days)
- [x] Wire up `get_current_user` and `get_current_org` dependencies
- [x] Add rate limiting on auth endpoints (Redis-based via slowapi)
- [x] Pydantic schemas for all auth request/response payloads
- [x] Verify: curl register → login → access protected endpoint

### Session 1.3: API Key Management & Core CRUD Routers ✅
**Done when:** API keys can be created/listed/revoked. Organization settings work.

- [x] API key router (`/api/v1/api-keys/`)
  - `POST /` — generate API key (return full key ONCE, store SHA-256 hash)
  - `GET /` — list keys (prefix only, never full key)
  - `DELETE /{id}` — revoke key (soft-delete)
  - `PATCH /{id}` — update name/scopes
- [x] Organization router (`/api/v1/organizations/`)
  - `GET /current` — get current org
  - `PATCH /current` — update org settings (admin-only)
  - `GET /current/members` — list members
- [x] Proxy endpoints router (`/api/v1/proxy-endpoints/`)
  - Full CRUD (5 endpoints) for configuring LLM proxy targets
- [x] API key authentication dependency (`get_current_org_from_api_key`)
- [x] Admin-only enforcement via `require_admin` dependency
- [x] Verify: 13 curl tests pass

### Session 1.4: Pydantic Schemas & Remaining CRUD Routers ✅
**Done when:** All remaining CRUD routers (detectors, incidents, alerts, dashboard) have schemas, services, and API endpoints.

- [x] Detector schemas, service (with rule management + selectinload), and router (7 endpoints)
- [x] Incident schemas, service (filters, status update, add action), and router (4 endpoints)
- [x] Alert destination schemas, service (CRUD + alert listing), and router (5 endpoints)
- [x] Dashboard schemas, service (aggregate metrics), and router (1 endpoint)
- [x] All schemas re-exported in `app/schemas/__init__.py` (34 schemas total)
- [x] Verify: 17 new endpoints curl-tested, pyright 0 errors

---

## Phase 2: LLM Proxy Engine (Weeks 3-4)

**Goal:** The core product — intercept, analyze, and forward LLM API calls with configurable detection.

### Session 2.1: Proxy Request Handler (OpenAI) ✅
**Done when:** Requests to AgentGuard proxy are forwarded to OpenAI and responses returned. All requests logged.

- [x] Implement proxy router (`/api/v1/proxy/`) with 3 endpoints:
  - `POST /v1/chat/completions` — streaming + non-streaming
  - `POST /v1/completions` — streaming + non-streaming
  - `POST /v1/embeddings` — non-streaming only
- [x] Request flow: auth (API key) → log request → resolve endpoint → forward via httpx → log response → return
- [x] Streaming support (SSE passthrough with `stream_options.include_usage` injection)
- [x] Cost calculation (static pricing table, longest-prefix model matching)
- [x] Error handling (timeout→504, connection→502, upstream errors passthrough)
- [x] Optional `X-AgentGuard-Endpoint-Id` header for multi-endpoint routing
- [x] 512KB body truncation for DB logging
- [x] Verify: All 3 endpoints forward to OpenAI, requests logged to DB with latency/status/model

### Session 2.2: Proxy Request Handler (Anthropic) ✅
**Done when:** Anthropic Messages API calls work through the proxy.

- [x] Add Anthropic proxy endpoint
  - `POST /v1/messages` — Anthropic Messages API compatible
- [x] Handle Anthropic-specific auth (x-api-key header forwarding)
- [x] Handle Anthropic streaming (SSE format differences — event: lines, content_block_delta, message_delta usage)
- [x] Anthropic cost calculation (8-model pricing table with prefix matching)
- [x] Normalize request/response logging (common schema across providers, provider-aware endpoint resolution)
- [x] Verify: Route registered, endpoint resolves to Anthropic, requests logged to DB, pyright 0 errors

### Session 2.3: Detection Pipeline Architecture
**Done when:** Detection pipeline processes every proxy response through configured detectors asynchronously.

- [ ] Design detection pipeline:
  1. Proxy response received
  2. Sync pre-response detectors run (block/redact decisions — PII, compliance)
  3. Response sent to client (with or without modifications)
  4. Async post-response detectors run via Celery (hallucination, cost, loop)
  5. Incidents created for any detections
  6. Alerts fired based on severity + destination config
- [ ] Implement `DetectionPipeline` service:
  - `run_sync_detectors(request, response)` → `DetectionResult` (pass/block/redact)
  - `queue_async_detectors(request_id)` → Celery task
- [ ] Implement `DetectionResult` model: `detected`, `severity`, `category`, `details`, `action`
- [ ] Implement detector loading: fetch org's active detectors, ordered by priority
- [ ] Verify: Proxy request triggers detection pipeline, Celery task queued

### Session 2.4: Rule-Based Detectors (PII, Cost, Loop)
**Done when:** PII, cost anomaly, and loop detectors create incidents when violations found.

- [ ] **PII Detector** (`app/services/detection/pii.py`):
  - Regex patterns: SSN, credit card, bank account, phone, email, DOB
  - Named entity recognition (spaCy or presidio) for names, addresses
  - Action modes: monitor (log), redact (mask PII in response), block (reject)
  - Configurable sensitivity levels
- [ ] **Cost Anomaly Detector** (`app/services/detection/cost.py`):
  - Track rolling average cost per org
  - Alert on requests >3x std deviation from org's baseline
  - Alert on cumulative daily spend exceeding configurable threshold
  - Token count anomaly detection (unusually large prompts/responses)
- [ ] **Loop Detector** (`app/services/detection/loop.py`):
  - Compare last N responses for similarity (cosine similarity or exact match)
  - Detect repeated tool call patterns
  - Configurable similarity threshold and window size
- [ ] Create incidents with proper severity levels (low/medium/high/critical)
- [ ] Verify: Send PII-containing request → incident created; Send similar requests → loop detected

### Session 2.5: LLM-Powered Detectors (Hallucination, Compliance)
**Done when:** Hallucination and compliance detectors work using AgentGuard's own LLM.

- [ ] **Hallucination Detector** (`app/services/detection/hallucination.py`):
  - Send response + context to AgentGuard's LLM for fact-checking
  - Structured prompt: "Does this response contain fabricated facts, invented citations, or unverifiable claims?"
  - Confidence score (0-1) with configurable threshold
  - Cache common patterns to reduce LLM costs
  - Async only (post-response) — never blocks client
- [ ] **Compliance Detector** (`app/services/detection/compliance.py`):
  - Rule-based first pass: keyword matching for regulated terms
  - LLM second pass: "Does this response violate [SOX/PCI-DSS/FFIEC] regulations?"
  - Pre-built regulatory rule sets:
    - SOX: Financial statement accuracy, internal controls
    - PCI-DSS: Cardholder data exposure
    - FFIEC: Fair lending language, risk disclosures
  - Configurable regulatory frameworks per org
- [ ] AgentGuard LLM service (separate API key management for internal LLM calls)
- [ ] Rate limiting on internal LLM calls (cost protection)
- [ ] Verify: Send hallucination-prone response → detected; Send compliance-violating content → detected

---

## Phase 3: Incident Management & Alerting (Week 5)

**Goal:** Full incident lifecycle management with multi-channel alerting.

### Session 3.1: Incident Management CRUD
**Done when:** Incidents can be viewed, filtered, updated, and have actions recorded.

- [ ] Incident router (`/api/v1/incidents/`)
  - `GET /` — list with filters (severity, category, status, date range, detector)
  - `GET /{id}` — detail with related request, actions, and detector info
  - `PATCH /{id}` — update status (open → investigating → resolved → dismissed)
  - `POST /{id}/actions` — add action (comment, assign, escalate, resolve)
  - `GET /stats` — aggregate counts by severity, category, status
- [ ] Incident service with:
  - Pagination (cursor-based for performance)
  - Full-text search on title/description
  - Bulk status updates
  - Auto-close after configurable inactivity period
- [ ] Audit log entries for all incident state changes
- [ ] Verify: Create incident via detection → view → investigate → resolve → audit trail exists

### Session 3.2: Alert System & Destinations
**Done when:** Alerts fire to Slack, email, and PagerDuty when incidents are created.

- [ ] Alert router (`/api/v1/alerts/`)
  - CRUD for alert destinations (Slack webhook, email, PagerDuty)
  - `GET /` — list alerts with status
  - `POST /test` — send test alert to destination
- [ ] Alert service:
  - Evaluate alert rules (severity threshold per destination)
  - Slack integration (webhook with rich message formatting)
  - Email integration (SMTP or SendGrid)
  - PagerDuty integration (Events API v2)
  - Retry logic with exponential backoff (3 retries)
  - Alert deduplication (don't spam for related incidents)
- [ ] Celery task for async alert delivery
- [ ] Verify: Detection creates incident → alert sent to configured Slack webhook

### Session 3.3: Webhook System
**Done when:** Customers can receive webhook notifications for incidents.

- [ ] Webhook router (`/api/v1/webhooks/`)
  - CRUD for webhook endpoints
  - Signature verification (HMAC-SHA256)
  - Event types: `incident.created`, `incident.resolved`, `detector.triggered`, `cost.threshold`
- [ ] Webhook delivery service:
  - Async delivery via Celery
  - Retry with exponential backoff
  - Delivery log with response status
  - Dead letter queue for failed deliveries
- [ ] Verify: Incident created → webhook fired → signature verifiable

---

## Phase 4: Frontend Dashboard (Weeks 6-7)

**Goal:** Full enterprise dashboard with real-time updates, analytics, and team management.

### Session 4.1: Auth Pages & Layout
**Done when:** Users can register, login, and see the authenticated dashboard layout.

- [ ] Auth pages:
  - `/login` — email/password form
  - `/register` — registration with org creation
  - `/forgot-password` — password reset flow
- [ ] Authenticated layout:
  - Sidebar navigation (Dashboard, Incidents, Detectors, Alerts, Settings, Docs)
  - Header with user menu, org switcher, notifications bell
  - Responsive design (desktop-first, mobile-friendly)
- [ ] Auth provider (React context):
  - Token storage (httpOnly cookies preferred, fallback to memory)
  - Auto-refresh on token expiry
  - Protected route wrapper
- [ ] API client hooks (TanStack Query):
  - `useAuth()` — login, register, logout, current user
  - Query client configuration with retry, stale time, error handling
- [ ] Verify: Register → login → see dashboard layout → refresh preserves session

### Session 4.2: Dashboard Overview Page
**Done when:** Dashboard shows real-time metrics, charts, and recent incidents.

- [ ] Dashboard API endpoint (`/api/v1/dashboard/`)
  - `GET /metrics` — total requests, incidents, detections by category, cost
  - `GET /time-series` — requests/incidents over time (configurable range)
  - `GET /detection-breakdown` — pie chart data by detector type
  - `GET /top-incidents` — most recent/severe incidents
- [ ] Dashboard page components:
  - Metric cards (total requests, active incidents, detection rate, cost saved)
  - Time series chart (requests + incidents over time) — Recharts or Chart.js
  - Detection breakdown (bar chart by category)
  - Recent incidents table (last 10, clickable)
  - System health status (proxy latency, uptime)
- [ ] Auto-refresh (polling every 10s initially, WebSocket later)
- [ ] Verify: Dashboard loads with real data from proxy requests + detections

### Session 4.3: Incidents Page
**Done when:** Incidents can be browsed, filtered, searched, and managed from the UI.

- [ ] Incidents list page:
  - Filterable table (severity, category, status, date range)
  - Search bar (full-text on title/description)
  - Bulk actions (resolve, dismiss selected)
  - Pagination (cursor-based)
  - Sort by severity, date, status
- [ ] Incident detail page:
  - Incident metadata (severity, category, detector, timestamp)
  - Original request/response viewer (syntax highlighted JSON)
  - Detection details (what was found, confidence score)
  - Action timeline (who did what, when)
  - Action buttons (investigate, resolve, dismiss, escalate)
  - Related incidents (same detector or request pattern)
- [ ] Verify: Navigate to incident → see details → take action → status updates

### Session 4.4: Detector Configuration & Proxy Settings
**Done when:** Customers can configure detectors and proxy endpoints from the UI.

- [ ] Detectors page:
  - List all detectors with status (active/inactive)
  - Configure each detector:
    - Action mode: monitor / warn / redact / block
    - Sensitivity/threshold sliders
    - Custom rules (regex patterns for PII, keywords for compliance)
  - Enable/disable individual detectors
  - Detector performance stats (detections count, false positive rate)
- [ ] Proxy endpoints page:
  - Add/edit/delete proxy endpoints
  - Provider selection (OpenAI / Anthropic)
  - API key configuration (target provider key)
  - Test connection button
  - Usage stats per endpoint
- [ ] API keys page:
  - Generate new keys
  - View active keys (prefix only)
  - Revoke keys
  - Copy key on creation (one-time display)
- [ ] Verify: Configure detector → proxy request → detection uses new config

### Session 4.5: Alerts, Settings & Team Management
**Done when:** Alert destinations, org settings, team management, and audit log viewer work.

- [ ] Alerts page:
  - Configure alert destinations (Slack, email, PagerDuty)
  - Set severity thresholds per destination
  - Test alert button
  - Alert history with delivery status
- [ ] Settings pages:
  - Organization profile (name, logo, plan)
  - Team management (invite, roles: admin/member/viewer, remove)
  - Security settings (SSO config, session timeout, IP allowlist)
  - Data retention settings
  - Billing portal (Stripe customer portal link)
- [ ] Audit log viewer:
  - Filterable table of all org actions
  - Export to CSV
  - Date range filter
- [ ] Verify: Configure alert destination → test alert → received

### Session 4.6: Real-Time Updates (WebSocket)
**Done when:** Dashboard and incidents page update in real-time via WebSocket.

- [ ] Backend WebSocket endpoint (`/ws/events`)
  - Authenticate via JWT token in query param
  - Event types: `incident.new`, `incident.updated`, `metrics.updated`, `alert.sent`
  - Per-org event routing (Redis pub/sub)
- [ ] Frontend WebSocket client:
  - Auto-connect on auth
  - Reconnect with exponential backoff
  - SSE fallback if WebSocket fails
  - TanStack Query cache invalidation on events
- [ ] Update dashboard metrics in real-time
- [ ] Toast notifications for new incidents
- [ ] Incident list auto-updates
- [ ] Verify: Create incident via proxy → dashboard updates without page refresh

---

## Phase 5: Billing, Onboarding & SSO (Week 8)

**Goal:** Stripe billing, customer onboarding wizard, and SSO integration.

### Session 5.1: Stripe Billing Integration
**Done when:** Customers can subscribe, upgrade, and manage billing. Usage is metered.

- [ ] Stripe setup:
  - Products: Starter ($99/mo), Pro ($499/mo), Enterprise (custom)
  - Usage metering: proxy requests/month
  - Webhook handler for subscription events
- [ ] Billing service:
  - Create Stripe customer on org registration
  - Subscription management (create, upgrade, cancel)
  - Usage reporting (report proxy request counts to Stripe)
  - Invoice webhook handling
  - Plan tier enforcement (rate limits, feature gates)
- [ ] Billing API endpoints:
  - `GET /api/v1/billing/subscription` — current plan
  - `POST /api/v1/billing/checkout` — Stripe Checkout session
  - `POST /api/v1/billing/portal` — Stripe Customer Portal session
  - `POST /api/v1/billing/webhook` — Stripe webhook handler
- [ ] Frontend billing page:
  - Current plan display
  - Upgrade/downgrade buttons
  - Usage meter (requests used / limit)
  - Invoice history
- [ ] Verify: Register → subscribe via Stripe → proxy requests metered → invoice generated

### Session 5.2: Onboarding Wizard
**Done when:** New users complete a guided setup in <5 minutes and see their first detection.

- [ ] Onboarding flow (after registration):
  1. Welcome → name your organization
  2. Create your first proxy endpoint (select provider, paste API key)
  3. Generate an API key (one-click copy)
  4. Integration guide (code snippets for Python, Node.js, curl)
  5. Send a test request (pre-built "try it" button)
  6. See your first detection (PII test payload)
  7. Configure alerts (optional — Slack webhook)
  8. Done → redirect to dashboard
- [ ] Track onboarding progress (resume where left off)
- [ ] Skip option for experienced users
- [ ] Verify: New registration → complete wizard → first incident visible on dashboard

### Session 5.3: SSO Integration (SAML/OIDC)
**Done when:** Organizations can configure SSO and members authenticate via their IdP.

- [ ] SSO service:
  - SAML 2.0 support (Okta, Azure AD, OneLogin)
  - OIDC support (Google Workspace, Auth0)
  - SP-initiated login flow
  - JIT (Just-In-Time) user provisioning
- [ ] SSO configuration UI:
  - Upload SAML metadata XML or configure OIDC endpoints
  - Test connection
  - Enforce SSO (disable password login for org)
- [ ] SSO login flow:
  - `/login/sso` — enter org slug → redirect to IdP
  - `/auth/callback` — handle IdP response → issue JWT
- [ ] Verify: Configure Okta SSO → login via Okta → user provisioned → dashboard access

---

## Phase 6: Compliance, Security & Data Retention (Week 9)

**Goal:** Production-grade security, compliance audit trails, and tiered data retention.

### Session 6.1: Audit Trail & Compliance
**Done when:** Every action is logged, audit trails are immutable, compliance reports can be generated.

- [ ] Comprehensive audit logging:
  - All API requests (who, what, when, from where)
  - All data access (who viewed what data)
  - All configuration changes
  - All incident state changes
  - All authentication events (login, logout, failed attempts)
- [ ] Audit log immutability:
  - Append-only table (no UPDATE/DELETE permissions)
  - Hash chain for tamper detection (each entry includes hash of previous)
- [ ] Compliance report generator:
  - Date range selection
  - Export formats: PDF, CSV
  - Report types: Access audit, incident summary, detection efficacy, configuration changes
- [ ] FFIEC/SOX report templates
- [ ] Verify: Take various actions → audit log entries exist → generate compliance report

### Session 6.2: Data Retention Pipeline
**Done when:** Data automatically moves from hot → warm → cold storage based on age.

- [ ] Tiered retention architecture:
  - **Hot (0-30 days):** PostgreSQL — full query capability
  - **Warm (30 days - 1 year):** S3 Standard — JSON exports, queryable via Athena
  - **Cold (1-7 years):** S3 Glacier — compressed archives, regulatory retention
- [ ] Retention Celery tasks:
  - Daily: Archive proxy_requests older than 30 days → S3 (batch export)
  - Monthly: Move S3 Standard objects older than 1 year → Glacier
  - Nightly: Cleanup PostgreSQL (delete archived records, VACUUM)
- [ ] Retention configuration per org (overridable)
- [ ] Archival metadata table (track what's archived where, for retrieval)
- [ ] Retrieval API for archived data (async — queue retrieval from Glacier)
- [ ] Verify: Create old test data → retention task runs → data in S3 → retrievable

### Session 6.3: Security Hardening
**Done when:** All OWASP Top 10 mitigated, encryption at rest/transit, security headers set.

- [ ] Application security:
  - CSRF protection on all state-changing endpoints
  - Content Security Policy headers
  - Strict CORS configuration (production domains only)
  - Request size limits (prevent abuse)
  - SQL injection prevention (parameterized queries — already via SQLAlchemy)
  - XSS prevention (output encoding, CSP)
- [ ] Encryption:
  - TLS 1.3 everywhere (enforced at load balancer)
  - Database encryption at rest (AWS RDS encryption)
  - API keys encrypted at rest (AES-256-GCM)
  - Sensitive fields in proxy_requests encrypted (request/response bodies)
- [ ] Authentication hardening:
  - Account lockout after 10 failed attempts (30 min cooldown)
  - Password complexity requirements (12+ chars, mixed)
  - Refresh token rotation on every use
  - Session invalidation on password change
- [ ] IP allowlisting (optional per org)
- [ ] Verify: Run OWASP ZAP scan → no high/critical findings

---

## Phase 7: Infrastructure & Deployment (Week 10)

**Goal:** Production AWS infrastructure, CI/CD pipeline, monitoring, and first deployment.

### Session 7.1: AWS Infrastructure (Terraform)
**Done when:** VPC, EKS cluster, RDS, ElastiCache, S3 created via Terraform.

- [ ] Terraform modules:
  - VPC (3 AZs, public/private subnets, NAT gateway)
  - EKS cluster (managed node groups, autoscaling)
  - RDS PostgreSQL 15 (Multi-AZ, encrypted, automated backups)
  - ElastiCache Redis 7 (cluster mode, encrypted)
  - S3 buckets (warm storage, cold storage, static assets)
  - ECR repositories (API, worker, frontend)
  - Secrets Manager (API keys, database credentials)
  - Route 53 (DNS)
  - ACM (SSL certificates)
  - ALB (Application Load Balancer with WAF)
- [ ] Environment separation: staging + production
- [ ] Cost estimation and budget alerts
- [ ] Verify: `terraform apply` creates all resources, RDS accessible from EKS

### Session 7.2: Kubernetes Manifests & Helm Charts
**Done when:** All services deployable to EKS with proper configs.

- [ ] Kubernetes manifests:
  - API deployment (3 replicas, HPA, readiness/liveness probes)
  - Worker deployment (2 replicas, HPA based on queue depth)
  - Beat deployment (1 replica, leader election)
  - Frontend deployment (2 replicas, Nginx)
  - Ingress (ALB Ingress Controller)
  - ConfigMaps and Secrets
  - NetworkPolicies (restrict inter-service communication)
  - PodDisruptionBudgets
- [ ] Helm chart for parameterized deployments
- [ ] Horizontal Pod Autoscaler configs (CPU + custom metrics)
- [ ] Verify: `helm install` deploys all services, health checks pass

### Session 7.3: CI/CD Pipeline (GitHub Actions)
**Done when:** Push to main triggers build → test → deploy to staging. Manual promotion to production.

- [ ] GitHub Actions workflows:
  - **PR checks:** lint, type check, unit tests, security scan
  - **Build:** Docker image build, push to ECR
  - **Deploy staging:** Auto-deploy on merge to main
  - **Deploy production:** Manual approval gate
  - **Database migrations:** Run on deploy (with rollback plan)
- [ ] Docker build optimization:
  - Multi-stage builds
  - Layer caching
  - Image scanning (Trivy)
- [ ] Release management:
  - Semantic versioning
  - Changelog generation
  - Rollback procedure documented
- [ ] Verify: Push code → CI passes → staging deployed → smoke test passes

### Session 7.4: Monitoring, Logging & Alerting
**Done when:** Sentry captures errors, structured logs are searchable, uptime monitoring active.

- [ ] Sentry integration:
  - Backend error tracking (FastAPI middleware)
  - Frontend error tracking (Next.js ErrorBoundary)
  - Release tracking (deploy notifications)
  - Performance monitoring (transaction tracing)
- [ ] Structured logging:
  - JSON log format (structlog)
  - Correlation IDs across request lifecycle
  - Log levels: ERROR → Sentry, WARN → review, INFO → audit
  - CloudWatch Logs integration
- [ ] Uptime monitoring:
  - Health check endpoints (API, proxy, database, Redis)
  - External uptime monitor (Better Uptime or Checkly)
  - Status page for customers
- [ ] Operational alerts:
  - API error rate >1% → Slack alert
  - P99 latency >500ms → Slack alert
  - Worker queue depth >1000 → auto-scale trigger
  - Database connection pool exhaustion → PagerDuty
- [ ] Verify: Trigger error → appears in Sentry with context → alert fires

---

## Phase 8: Testing, Docs & Launch Prep (Week 10-11)

**Goal:** Comprehensive test coverage, developer docs, and production readiness.

### Session 8.1: Backend Test Suite
**Done when:** 80%+ backend coverage, all critical paths tested.

- [ ] Unit tests:
  - All detection algorithms (PII, hallucination, compliance, cost, loop)
  - Auth service (register, login, token refresh, permissions)
  - Proxy request handling (OpenAI, Anthropic)
  - Billing service (subscription, metering)
  - Data retention service
- [ ] Integration tests:
  - Full proxy flow (request → detect → incident → alert)
  - Auth flow (register → login → access → refresh → logout)
  - API key lifecycle (create → authenticate → revoke)
  - WebSocket events
- [ ] Fixtures and factories:
  - Database fixtures (orgs, users, detectors)
  - Request/response fixtures (real-ish LLM payloads)
  - Mock LLM responses for detector testing
- [ ] Verify: `pytest tests/ -v` — 80%+ coverage, 0 failures

### Session 8.2: Frontend Test Suite
**Done when:** Component tests for all major UI elements, E2E for critical flows.

- [ ] Component tests (React Testing Library):
  - Auth forms (login, register)
  - Dashboard metrics cards
  - Incident table and detail view
  - Detector configuration forms
  - Alert destination forms
  - Onboarding wizard steps
- [ ] E2E tests (Playwright):
  - Full registration → onboarding → first detection flow
  - Incident management lifecycle
  - Detector configuration → proxy request → detection
  - Billing subscription flow (Stripe test mode)
- [ ] Verify: `npm test` passes, `npx playwright test` passes

### Session 8.3: Developer Documentation & SDK
**Done when:** API docs, integration guides, and a lightweight Python/Node SDK published.

- [ ] API documentation:
  - OpenAPI spec auto-generated (FastAPI)
  - Hosted at `/docs` (Swagger UI) and `/redoc` (ReDoc)
  - Authentication guide
  - Rate limiting documentation
  - Error code reference
- [ ] Integration guides:
  - Quick start (5-minute setup)
  - Python integration (openai SDK → AgentGuard proxy)
  - Node.js integration
  - Custom LLM integration
- [ ] Lightweight SDK (Python):
  - `pip install agentguard`
  - Wraps proxy endpoint configuration
  - `agentguard.wrap(openai_client)` — monkey-patch approach
- [ ] Verify: Follow quick start guide from scratch → working in 5 minutes

### Session 8.4: Production Launch Checklist
**Done when:** All items checked, production is live.

- [ ] Security review:
  - [ ] OWASP ZAP scan — no high/critical
  - [ ] Dependency audit (`pip-audit`, `npm audit`) — no critical
  - [ ] Secrets scan — no hardcoded credentials
  - [ ] CORS, CSP, security headers verified
  - [ ] Rate limiting tested under load
- [ ] Performance:
  - [ ] Proxy latency <50ms overhead (p95)
  - [ ] Dashboard loads <2s
  - [ ] WebSocket reconnection works
  - [ ] Database query performance (no N+1, indexes verified)
- [ ] Reliability:
  - [ ] Health checks on all services
  - [ ] Auto-scaling verified
  - [ ] Failover tested (kill a pod, verify recovery)
  - [ ] Database backup/restore tested
  - [ ] Rollback procedure tested
- [ ] Compliance:
  - [ ] Audit trail complete
  - [ ] Data retention working
  - [ ] Encryption at rest verified
  - [ ] Privacy policy and ToS published
- [ ] Operational:
  - [ ] Monitoring and alerting active
  - [ ] On-call runbook written
  - [ ] Status page live
  - [ ] Support email configured
  - [ ] Domain and SSL configured
- [ ] Business:
  - [ ] Stripe billing live
  - [ ] Pricing page published
  - [ ] Landing page updated
  - [ ] Analytics tracking (PostHog or similar)

---

## Architecture Decisions

### 1. LLM Proxy Pattern
All customer LLM traffic routes through AgentGuard. This is the core architectural decision — it provides:
- Complete visibility into all AI interactions
- Real-time intervention capability
- Zero client-side code changes (just swap the base URL)
- Provider-agnostic detection

### 2. Sync vs Async Detection
- **Sync (pre-response):** PII redaction and compliance blocking. These run BEFORE the response reaches the customer. Must be <50ms.
- **Async (post-response):** Hallucination, cost anomaly, loop detection. These run via Celery AFTER the response is sent. Can take seconds.

### 3. Multi-Tenant Isolation
Every database query includes `org_id`. This is enforced at the service layer, not just the API layer. Defense in depth:
- API layer: `get_current_org()` dependency
- Service layer: all queries filter by `org_id`
- Database layer: Row-level security policies (phase 2)

### 4. API Key Authentication (Proxy) vs JWT (Dashboard)
- Proxy requests use API keys (stateless, low-latency, machine-to-machine)
- Dashboard uses JWT (user sessions, refresh tokens, SSO)
- Two separate auth flows, shared user/org model

### 5. Tiered Data Retention
Financial regulations require 7-year retention. PostgreSQL for hot data (30d), S3 for warm (1yr), Glacier for cold (7yr). Automated pipeline moves data through tiers.

### 6. WebSocket for Real-Time
Redis pub/sub for inter-process event routing. WebSocket connections per-org. SSE fallback for environments where WebSocket is blocked.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Solo developer bus factor | Comprehensive CLAUDE.md, clean architecture, full test coverage |
| LLM detection accuracy | Start with high-precision rule-based, add LLM detection iteratively with human review |
| Proxy latency impact | Sync detectors budget: <50ms. Async for everything else |
| AWS cost overrun | Budget alerts, reserved instances, right-sized resources |
| Security breach | Encryption everywhere, audit logs, regular security scans, minimal data retention |
| Customer data leak between tenants | org_id on every query, integration tests verifying isolation |
| Scaling bottleneck | HPA on all services, database read replicas ready, Redis cluster mode |

---

## File Structure (Target)

### Backend (`agentguard-backend/backend/app/`)
```
api/
├── auth.py              # Auth endpoints
├── proxy.py             # LLM proxy endpoints
├── incidents.py         # Incident CRUD
├── detectors.py         # Detector configuration
├── alerts.py            # Alert destinations
├── dashboard.py         # Dashboard metrics
├── webhooks.py          # Webhook management
├── api_keys.py          # API key management
├── organizations.py     # Org management
├── billing.py           # Stripe billing
└── websocket.py         # WebSocket events

models/
├── __init__.py
├── user.py
├── organization.py
├── api_key.py
├── proxy_endpoint.py
├── proxy_request.py
├── incident.py
├── incident_action.py
├── detector.py
├── detector_rule.py
├── alert.py
├── alert_destination.py
└── audit_log.py

services/
├── auth_service.py
├── proxy_service.py
├── incident_service.py
├── alert_service.py
├── billing_service.py
├── retention_service.py
├── audit_service.py
├── webhook_service.py
└── detection/
    ├── __init__.py
    ├── pipeline.py        # Detection orchestrator
    ├── pii.py             # PII detector
    ├── hallucination.py   # Hallucination detector
    ├── compliance.py      # Compliance detector
    ├── cost.py            # Cost anomaly detector
    └── loop.py            # Loop detector

schemas/
├── auth.py
├── proxy.py
├── incidents.py
├── detectors.py
├── alerts.py
├── dashboard.py
├── organizations.py
├── billing.py
└── common.py

tasks/
├── detection.py         # Async detection tasks
├── alerts.py            # Alert delivery tasks
├── retention.py         # Data archival tasks
├── reports.py           # Report generation
└── billing.py           # Usage reporting to Stripe
```

### Frontend (`agentguard-frontend/src/`)
```
app/
├── (auth)/
│   ├── login/page.tsx
│   ├── register/page.tsx
│   └── forgot-password/page.tsx
├── (dashboard)/
│   ├── layout.tsx           # Sidebar + header
│   ├── page.tsx             # Dashboard overview
│   ├── incidents/
│   │   ├── page.tsx         # Incident list
│   │   └── [id]/page.tsx    # Incident detail
│   ├── detectors/page.tsx
│   ├── proxy/page.tsx
│   ├── alerts/page.tsx
│   ├── settings/
│   │   ├── page.tsx         # Org settings
│   │   ├── team/page.tsx
│   │   ├── security/page.tsx
│   │   ├── billing/page.tsx
│   │   └── audit/page.tsx
│   └── onboarding/page.tsx
├── (marketing)/
│   ├── page.tsx             # Landing page
│   ├── pricing/page.tsx
│   └── docs/page.tsx
└── api/                     # Next.js API routes (if needed)

components/
├── layout/
│   ├── Sidebar.tsx
│   ├── Header.tsx
│   └── MobileNav.tsx
├── dashboard/
│   ├── MetricCards.tsx
│   ├── TimeSeriesChart.tsx
│   ├── DetectionBreakdown.tsx
│   └── RecentIncidents.tsx
├── incidents/
│   ├── IncidentTable.tsx
│   ├── IncidentDetail.tsx
│   ├── IncidentFilters.tsx
│   └── ActionTimeline.tsx
├── detectors/
│   ├── DetectorCard.tsx
│   ├── DetectorConfig.tsx
│   └── ActionModeSelector.tsx
├── onboarding/
│   ├── OnboardingWizard.tsx
│   └── steps/
├── ui/                      # Shared UI components (shadcn/ui)
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── Dialog.tsx
│   ├── Table.tsx
│   └── ...
└── providers/
    ├── AuthProvider.tsx
    ├── WebSocketProvider.tsx
    └── ThemeProvider.tsx

hooks/
├── useAuth.tsx
├── useWebSocket.tsx
├── api/
│   ├── useIncidents.ts
│   ├── useDetectors.ts
│   ├── useDashboard.ts
│   ├── useAlerts.ts
│   ├── useProxy.ts
│   └── useBilling.ts
└── useOnboarding.ts

lib/
├── api/
│   ├── client.ts           # Base API client
│   ├── incidents.ts
│   ├── detectors.ts
│   ├── dashboard.ts
│   ├── alerts.ts
│   ├── proxy.ts
│   ├── billing.ts
│   └── auth.ts
├── websocket.ts
└── utils.ts

types/
├── incidents.ts
├── detectors.ts
├── dashboard.ts
├── alerts.ts
├── proxy.ts
├── billing.ts
├── auth.ts
└── common.ts
```

---

## Weekly Velocity Targets

| Week | Phase | Sessions | Deliverable |
|------|-------|----------|-------------|
| 1 | Foundation | 1.1, 1.2 | Models + Auth working |
| 2 | Foundation | 1.3, 1.4 | API keys + all schemas |
| 3 | Proxy | 2.1, 2.2 | OpenAI + Anthropic proxy working |
| 4 | Proxy | 2.3, 2.4, 2.5 | All 5 detectors working |
| 5 | Incidents | 3.1, 3.2, 3.3 | Incident management + alerting |
| 6 | Frontend | 4.1, 4.2, 4.3 | Auth + dashboard + incidents UI |
| 7 | Frontend | 4.4, 4.5, 4.6 | Detectors + settings + WebSocket |
| 8 | Billing | 5.1, 5.2, 5.3 | Stripe + onboarding + SSO |
| 9 | Security | 6.1, 6.2, 6.3 | Compliance + retention + hardening |
| 10 | Infra | 7.1, 7.2, 7.3, 7.4 | AWS + K8s + CI/CD + monitoring |
| 11 | Testing | 8.1, 8.2, 8.3 | Full test suite + docs + SDK |
| 12 | Launch | 8.4 | Production launch |

---

## Session Protocol

Every coding session follows this protocol:

1. **Start:** Read this plan, identify next uncompleted session
2. **Execute:** Implement all items in the session
3. **Verify:** Type check, functional test, no regressions
4. **Commit:** Conventional commit message, push to remote
5. **Update:** Mark session complete, note any blockers

**No session ends without a working, verified, pushed commit.**
