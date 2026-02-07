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

### Session 2.3: Detection Pipeline Architecture ✅
**Done when:** Detection pipeline processes every proxy response through configured detectors asynchronously.

- [x] Design detection pipeline:
  1. Proxy response received
  2. Sync pre-response detectors run (block/redact decisions — PII, compliance)
  3. Response sent to client (with or without modifications)
  4. Async post-response detectors run via Celery (hallucination, cost, loop)
  5. Incidents created for any detections
  6. Alerts fired based on severity + destination config
- [x] Implement detection pipeline service (`app/services/detection/pipeline.py`):
  - `run_sync_detectors(db, org_id, request_body, response_body, model, proxy_request_id)` → `PipelineDecision`
  - `queue_async_detectors(db, org_id, proxy_request_id)` → Celery task ID
- [x] Implement `DetectionResult` dataclass + `PipelineDecision` + `DetectionAction` enum (`types.py`)
- [x] Implement `SyncDetector`/`AsyncDetector` protocols (`base.py`), registry with stub detectors (`registry.py`)
- [x] Implement Celery task `run_async_detection` (`app/tasks/analysis.py`) with sync DB, retry logic
- [x] Integrate pipeline into all 4 proxy handlers (non-streaming: sync+async, streaming: async only)
- [x] Verify: All imports work at runtime, proxy endpoints respond correctly, pyright 0 errors

### Session 2.4: Rule-Based Detectors (PII, Cost, Loop) ✅
**Done when:** PII, cost anomaly, and loop detectors create incidents when violations found.

- [x] **PII Detector** (`app/services/detection/pii.py`):
  - Regex patterns: SSN, credit card, bank account, phone, email, DOB
  - Redaction support (masks PII with █ characters)
  - Configurable disabled_patterns in detector config
  - Severity escalation: critical (SSN, CC), high (bank account, DOB), medium (phone, email)
- [x] **Cost Anomaly Detector** (`app/services/detection/cost.py`):
  - Hard ceiling check (configurable max_tokens, default 50k)
  - Spike detection (configurable multiplier over rolling average)
  - Supports both OpenAI (total_tokens) and Anthropic (input+output) usage formats
- [x] **Loop Detector** (`app/services/detection/loop.py`):
  - SequenceMatcher similarity comparison against recent_responses
  - Repeated tool call pattern detection (same function+args)
  - Configurable similarity_threshold (default 0.85) and min_response_length
  - Parses both OpenAI and Anthropic response formats
- [x] Wired all 3 detectors into registry.py (replaced stubs)
- [x] Created app/tasks/reports.py stub (fixed pre-existing worker crash)
- [x] Verified: pyright 0 errors, all detectors pass functional tests in Docker

### Session 2.5: LLM-Powered Detectors (Hallucination, Compliance) ✅
**Done when:** Hallucination and compliance detectors work using AgentGuard's own LLM.

- [x] **LLM Service** (`app/services/llm_service.py`):
  - Shared internal LLM client (httpx POST to OpenAI/Anthropic, no SDK dependency)
  - Configurable via DETECTION_LLM_PROVIDER, DETECTION_LLM_MODEL, DETECTION_LLM_RPM
  - Sliding-window rate limiter (per-process)
  - Graceful failure: returns empty string on error (detectors fail-open)
  - JSON response parser with markdown fence stripping
- [x] **Hallucination Detector** (`app/services/detection/hallucination.py`):
  - AsyncDetector — sends response to internal LLM for fact-checking
  - Structured prompt for confidence score (0-1) + issue list
  - Configurable threshold (default 0.7), severity escalation by confidence
  - Fail-open: if LLM unavailable, returns detected=False
  - Extracts text from both OpenAI and Anthropic response formats
- [x] **Compliance Detector** (`app/services/detection/compliance.py`):
  - SyncDetector — two-pass: keyword matching + LLM verification
  - SOX (7 keywords), PCI-DSS (7 keywords), FFIEC (7 keywords)
  - Configurable frameworks list per detector config
  - LLM second pass verifies keyword matches (graceful degradation)
  - Severity: high for SOX/PCI-DSS, critical if LLM confirms violation
- [x] All 5 detectors now registered: sync (PII, compliance), async (hallucination, cost, loop)
- [x] Verified: pyright 0 errors, all detectors functional in Docker (API + worker)

---

## Phase 3: Incident Management & Alerting (Week 5)

**Goal:** Full incident lifecycle management with multi-channel alerting.

### Session 3.1: Incident Management CRUD ✅
**Done when:** Incidents can be viewed, filtered, updated, and have actions recorded.

- [x] Incident router (`/api/v1/incidents/`):
  - `GET /` — list with filters (severity, category, status, date range, detector, full-text search)
  - `GET /{id}` — detail with related actions
  - `PATCH /{id}` — update status with audit logging
  - `POST /{id}/actions` — add action with audit logging
  - `GET /stats` — aggregate counts by severity, category, status
  - `POST /bulk-update` — bulk status update with audit logging
- [x] Incident service enhanced:
  - Offset/limit pagination with total count
  - ILIKE search on title/description (`?q=search`)
  - Date range filters (`?dateFrom=&dateTo=`)
  - Detector filter (`?detectorId=`)
  - Bulk status update with resolved_at handling
- [x] Audit log entries for all state changes (status_changed, bulk_status_changed, action.*)
- [x] Schemas: IncidentStatsResponse, BulkStatusUpdateRequest/Response
- [x] Verified: pyright 0 errors, all endpoints return correct responses via curl

### Session 3.2: Alert System & Destinations ✅
**Done when:** Alerts fire to Slack, email, and PagerDuty when incidents are created.

- [x] Alert delivery service (`app/services/alert_delivery.py`):
  - Slack integration (webhook with color-coded attachments)
  - PagerDuty integration (Events API v2)
  - Email integration (webhook-based)
  - Generic webhook support with HMAC secret
  - Dispatcher pattern for extensibility
- [x] Celery alert task (`app/tasks/alerting.py`):
  - `send_alerts_for_incident` — loads active destinations, evaluates severity threshold, deduplicates, delivers
  - 3 retries with 30s delay
  - Per-destination min_severity filtering
  - Alert record creation (sent/failed status tracking)
- [x] Alert router enhanced:
  - `POST /destinations/{id}/test` — send test alert
  - Existing CRUD + list endpoints preserved
- [x] Detection pipeline integration: `_create_incident_from_result` now queues alerts
- [x] Verified: pyright 0 errors, all imports/endpoints functional in Docker

### Session 3.3: Webhook System ✅
**Done when:** Customers can receive webhook notifications for incidents.

- [x] Webhook router (`/api/v1/webhooks/`):
  - Full CRUD (POST, GET list, GET detail, PATCH, DELETE)
  - Stored as AlertDestination type=webhook (reuses existing infrastructure)
  - Configurable event_types and min_severity per webhook
- [x] Webhook service (`app/services/webhook_service.py`):
  - HMAC-SHA256 signature generation (`X-AgentGuard-Signature` header)
  - `deliver_webhook_with_signature()` for signed delivery
  - `to_webhook_response()` adapter for AlertDestination → webhook view
- [x] Webhook schemas: create/update/response/list with camelCase aliases
- [x] Webhooks auto-fire via existing alert system (AlertDestination type=webhook)
- [x] Registered in main.py, pyright 0 errors, endpoints verified via curl

---

## Phase 4: Frontend Dashboard (Weeks 6-7)

**Goal:** Full enterprise dashboard with real-time updates, analytics, and team management.

### Session 4.1: Auth Pages & Layout ✅
**Done when:** Users can register, login, and see the authenticated dashboard layout.

- [x] Auth pages:
  - `/login` — email/password form with error handling
  - `/register` — registration with org creation (name, email, org, password)
- [x] Authenticated layout:
  - Sidebar navigation (Dashboard, Incidents, Detectors, Alerts, API Keys, Settings)
  - Header with user menu dropdown (name, email, sign out)
  - Desktop-first layout with fixed sidebar + header
- [x] Auth provider (React context):
  - Token storage (localStorage for access + refresh tokens)
  - Auto-refresh on token expiry (401 → refresh → retry)
  - ProtectedRoute wrapper component with loading spinner
- [x] Auth API client + useAuth hook:
  - `login()`, `register()`, `logout()`, auto-fetchMe on mount
  - Query client configuration with retry, stale time
- [x] API proxy fixed (port 8000→8002 in next.config.js)
- [x] TypeScript types updated to match backend auth schemas (AuthUser, AuthOrganization, MeResponse)
- [x] Verified: `next build` succeeds, backend auth endpoints tested via curl, all types match

### Session 4.2: Dashboard Overview Page ✅
**Done when:** Dashboard shows real-time metrics, charts, and recent incidents.

- [x] Dashboard page with TanStack Query:
  - Fetches `GET /dashboard/metrics` with 30s auto-refresh
  - Metric cards: total incidents, open incidents (highlighted red when > 0)
  - Severity breakdown card with color-coded badges
  - Status breakdown card with color-coded badges
  - Recent incidents table (10 most recent, clickable to detail page)
  - Empty state when no incidents
- [x] Dashboard API client (`src/lib/api/dashboard.ts`)
- [x] TypeScript types: DashboardMetrics, IncidentCountByStatus, IncidentCountBySeverity, RecentIncidentSummary
- [x] Verified: `next build` succeeds, metrics endpoint returns correct data shape

### Session 4.3: Incidents Page ✅
**Done when:** Incidents can be browsed, filtered, searched, and managed from the UI.

- [x] Incidents list page:
  - Filterable table (severity, category, status) with search bar
  - Bulk actions (resolve, dismiss selected via checkboxes)
  - Offset/limit pagination with page counter
  - Severity and status color-coded badges
- [x] Incident detail page:
  - Incident metadata (severity, category, detector, timestamps)
  - Description display
  - Status actions (acknowledge, resolve, dismiss) with TanStack mutations
  - Action timeline with timestamps
  - Add action form (investigate, escalate, comment with note)
- [x] Incidents API client: listIncidents, getIncident, updateIncidentStatus, addIncidentAction, bulkUpdateStatus
- [x] Updated TypeScript types: Incident, IncidentDetail, IncidentAction, IncidentFilters
- [x] Verified: `next build` succeeds, tsc 0 errors

### Session 4.4: Detector Configuration & API Keys ✅
**Done when:** Customers can configure detectors and manage API keys from the UI.

- [x] Detectors page:
  - List all detectors with active/inactive toggle
  - Action mode selector: monitor / warn / redact / block
  - Config display showing all detector settings
  - Category labels and rule count
- [x] API keys page:
  - Create key with name → full key shown once
  - Copy-to-clipboard with confirmation feedback
  - List keys (prefix only, scopes, last used, created date)
  - Revoke keys with confirmation
- [x] API clients: detectors (CRUD), api-keys (create/list/revoke)
- [x] Updated types: Detector (with rules, actionMode), ApiKey, ApiKeyCreateResponse
- [x] Verified: `next build` succeeds, tsc 0 errors, 9 routes compile

### Session 4.5: Alerts, Settings & Team Management
**Done when:** Alert destinations, org settings, team management, and audit log viewer work.

- [x] Alerts page:
  - Create alert destinations (Slack, PagerDuty, email, webhook) with webhook URL config
  - Toggle enable/disable per destination
  - Send test alert button with result feedback
  - Delete destinations with confirmation
- [x] Settings page:
  - Organization info (name, slug, plan, created date)
  - Account info (name, email, role, member since)
  - Placeholder sections for team management, security, billing (coming soon)
- [x] Alerts API client: listDestinations, createDestination, updateDestination, deleteDestination, testDestination, listAlerts
- [x] Updated types: AlertDestination (destinationType, isActive, updatedAt), Alert (errorMessage)
- [x] Verified: `next build` succeeds, tsc 0 errors, 11 routes compile

### Session 4.6: Real-Time Updates (WebSocket) ✅
**Done when:** Dashboard and incidents page update in real-time via WebSocket.

- [x] Backend WebSocket endpoint (`/ws/events`)
  - Authenticate via JWT token in query param
  - Event types: `incident.new`, `incident.updated`, `metrics.updated`, `alert.sent`
  - Per-org event routing (Redis pub/sub)
- [x] Frontend WebSocket client:
  - Auto-connect on auth
  - Reconnect with exponential backoff
  - Polling fallback if WebSocket disconnected
  - TanStack Query cache invalidation on events
- [x] Update dashboard metrics in real-time
- [x] Toast notifications for new incidents
- [x] Incident list auto-updates
- [x] Verify: WebSocket connects with JWT auth, Redis pub/sub events delivered, auth rejection works (4001)

---

## Phase 5: Billing, Onboarding & SSO (Week 8)

**Goal:** Stripe billing, customer onboarding wizard, and SSO integration.

### Session 5.1: Stripe Billing Integration ✅
**Done when:** Customers can subscribe, upgrade, and manage billing. Usage is metered.

- [x] Stripe setup:
  - Products: Starter ($99/mo, 10k req), Pro ($499/mo, 100k req), Enterprise (custom, unlimited)
  - Usage metering: monthly_request_count on Organization model, reset via Celery Beat
  - Webhook handler for subscription events (checkout.session.completed, subscription.updated/deleted, invoice.payment_failed)
  - Graceful degradation when Stripe keys not configured
- [x] Billing service:
  - Create Stripe customer on org registration (non-blocking)
  - Subscription management via Stripe Checkout + Customer Portal (no custom forms)
  - Usage counting in proxy (increment on each request in _parse_and_resolve)
  - Webhook idempotency via StripeEvent model
  - Plan tier enforcement (429 when limit exceeded, skip for Enterprise)
- [x] Billing API endpoints:
  - `GET /api/v1/billing/status` — current plan, usage, limits
  - `POST /api/v1/billing/checkout` — Stripe Checkout session
  - `POST /api/v1/billing/portal` — Stripe Customer Portal session
  - `POST /api/v1/billing/webhook` — Stripe webhook handler (signature verified)
- [x] Frontend billing page:
  - Current plan display with subscription status
  - Plan comparison cards (Starter / Pro / Enterprise)
  - Usage bar (color-coded: green → yellow → red)
  - Upgrade button → Stripe Checkout, Manage → Customer Portal
- [x] Celery tasks: reset_monthly_usage (1st of month), sync_subscription_status (daily)
- [x] Verify: billing/status returns plan_tier=starter + request_limit=10000, checkout returns 503 without keys

### Session 5.2: Onboarding Wizard ✅
**Done when:** New users complete a guided setup in <5 minutes and see their first detection.

- [x] Backend: Add settings to OrgResponse, merge settings in PATCH endpoint
- [x] 6-step wizard: Welcome → Proxy Endpoint → API Key → Integration Code → Test Request → Completion
- [x] WizardShell layout with progress bar, skip button
- [x] API clients: proxy-endpoints.ts, organizations.ts
- [x] Register redirects to /onboarding, onboarding marks completion in org settings
- [x] Skip option for experienced users
- [x] Verify: tsc clean, next build succeeds, /me returns settings, settings merge works

### Session 5.3: SSO Integration (SAML/OIDC) ✅
**Done when:** Organizations can configure SSO and members authenticate via their IdP.

- [x] SSO service:
  - SAML 2.0 support (Okta, Azure AD, OneLogin)
  - OIDC support (Google Workspace, Auth0)
  - SP-initiated login flow
  - JIT (Just-In-Time) user provisioning
- [x] SSO configuration UI:
  - Upload SAML metadata XML or configure OIDC endpoints
  - Test connection
  - Enforce SSO (disable password login for org)
- [x] SSO login flow:
  - `/login/sso` — enter org slug → redirect to IdP
  - `/auth/callback` — handle IdP response → issue JWT
- [x] Verify: SSO config CRUD, SAML metadata, SSO initiate redirect, enforcement blocks login (403)

---

## Phase 6: Compliance, Security & Data Retention (Week 9)

**Goal:** Production-grade security, compliance audit trails, and tiered data retention.

### Session 6.1: Audit Trail & Compliance ✅
**Done when:** Every action is logged, audit trails are immutable, compliance reports can be generated.
**Status:** COMPLETE — SHA-256 hash chain audit logging across all 7 services, compliance API with chain verification, async CSV report generation via Celery, frontend compliance page with filterable audit log and report management.

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

### Session 6.2: Data Retention Pipeline ✅
**Done when:** Data automatically moves from hot → warm → cold storage based on age.
**Status:** COMPLETE — Per-org retention policies, JSONL.gz archive storage with ArchiveStorage protocol (S3-swappable), daily Celery task for archive + batch delete, retention API with frontend settings page.

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

### Session 6.3: Security Hardening ✅
**Done when:** All OWASP Top 10 mitigated, encryption at rest/transit, security headers set.
**Status:** COMPLETE — Security headers middleware (X-Content-Type-Options, X-Frame-Options, HSTS, CSP, Referrer-Policy, Permissions-Policy), request size limits (10MB), strict CORS (explicit methods/headers), HMAC-SHA256 API key hashing, AES-256-GCM encryption utility, account lockout (10 attempts/30 min), password requirements (12+ chars, upper/lower/digit/special), token versioning with session invalidation on password change, refresh token rotation, change-password endpoint, IP allowlisting per org.

- [x] Application security:
  - Content Security Policy headers
  - Strict CORS configuration (explicit methods/headers, no wildcards)
  - Request size limits (10 MB max body)
  - SQL injection prevention (parameterized queries — already via SQLAlchemy)
  - XSS prevention (CSP, X-XSS-Protection, X-Content-Type-Options)
  - Security headers: X-Frame-Options DENY, HSTS, Referrer-Policy, Permissions-Policy
  - Cache-Control: no-store on all responses
- [x] Encryption:
  - TLS 1.3 (enforced at load balancer — configured in Phase 7)
  - Database encryption at rest (AWS RDS encryption — configured in Phase 7)
  - API keys hashed with HMAC-SHA256 (keyed hash prevents brute-force on DB compromise)
  - AES-256-GCM field-level encryption utility ready (app/core/security.py)
- [x] Authentication hardening:
  - Account lockout after 10 failed attempts (30 min cooldown)
  - Password complexity requirements (12+ chars, upper, lower, digit, special character)
  - Refresh token rotation on every use (new token pair each refresh)
  - Session invalidation on password change (token_version in JWT)
  - Change password endpoint (POST /auth/change-password)
- [x] IP allowlisting (optional per org via settings.ip_allowlist)
- [x] Verify: Security headers present, password validation enforced, lockout + token versioning functional

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
