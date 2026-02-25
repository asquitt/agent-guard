# Security Audit Tracker

## auth.py
- Status: CLEAN
- Endpoints: 11
- Issues found: 0
- Issues fixed: 0
- Details:
  - All endpoints have appropriate auth guards (get_current_user or public by design)
  - Rate limiting on register (5/min), login (5/min), refresh (10/min), forgot-password (3/min), reset-password (5/min)
  - Password strength validation (12+ chars, upper/lower/digit/special)
  - Account lockout after MAX_FAILED_LOGIN_ATTEMPTS
  - Token versioning for session invalidation on password change
  - Anti-enumeration on forgot-password (always returns 200)
  - Audit logging on all auth events
  - SSO enforcement check on login
  - Pydantic schemas for all request bodies

## proxy.py
- Status: CLEAN
- Endpoints: 4
- Issues found: 0
- Issues fixed: 0
- Details:
  - API key auth via get_current_org_from_api_key
  - Redis sliding-window rate limiting per org
  - IP allowlist enforcement
  - Circuit breaker for provider failures
  - Billing cap enforcement
  - No raw API keys in logs (masked)
  - Pydantic schemas for requests

## organizations.py
- Status: FIXED
- Endpoints: 12
- Issues found: 3
- Issues fixed: 3
- Details:
  - FIXED: `list_roles()` had NO auth guard (completely public) -- added `Depends(get_current_user)`
  - FIXED: `update_member_role` used `user_id: str` path param -- changed to `user_id: UUID` (prevents malformed input)
  - FIXED: `remove_member` used `user_id: str` path param -- changed to `user_id: UUID`, removed unnecessary PyUUID conversion
  - All write endpoints correctly use `require_admin`
  - Read endpoints use `require_permission("settings:read")`
  - Tenant isolation: all member queries filter by `org_id`
  - IP allowlist validation uses `ipaddress` stdlib (safe)
  - Pydantic schemas with field constraints on all request bodies

## api_keys.py
- Status: CLEAN
- Endpoints: 5
- Issues found: 0
- Issues fixed: 0
- Details:
  - All endpoints require `require_admin` + `get_current_org`
  - Rate limiting on create (10/min)
  - API key hashed (SHA-256) before storage, never stored plaintext
  - Key prefix shown only on creation, masked after
  - Tenant isolation: all queries filter by `org_id`
  - Pydantic schemas for all request bodies

## sso.py
- Status: FIXED
- Endpoints: 10
- Issues found: 1
- Issues fixed: 1
- Details:
  - FIXED: OIDC callback did NOT validate `state` parameter (CSRF risk) -- now stores state in Redis on initiate, validates + deletes on callback (one-time use, 5-min TTL)
  - Admin endpoints correctly use `require_admin`
  - Public endpoints (check, initiate, ACS, callback, metadata) are intentionally public for SSO flow
  - SAML response validated via python3-saml library
  - Secrets masked in response (oidc_client_secret_set bool, not raw)
  - JIT user provisioning with org tenant isolation

## incidents.py
- Status: CLEAN
- Endpoints: 7
- Issues found: 0
- Issues fixed: 0
- Details:
  - All endpoints use RBAC permissions (`incidents:read`, `incidents:write`)
  - Tenant isolation: all queries filter by `org_id`
  - Path parameter IDs validated as UUID type
  - Bulk operations filter by org ownership
  - Pydantic schemas for all request bodies

## detectors.py
- Status: CLEAN
- Endpoints: 6
- Issues found: 0
- Issues fixed: 0
- Details:
  - All endpoints use RBAC permissions (`detectors:read`, `detectors:write`)
  - Tenant isolation: all queries filter by `org_id`
  - Path parameter IDs validated as UUID type
  - Pydantic schemas for all request bodies

## alerts.py
- Status: CLEAN
- Endpoints: 7
- Issues found: 0
- Issues fixed: 0
- Details:
  - All endpoints use RBAC permissions (`alerts:read`, `alerts:write`)
  - Tenant isolation: all queries filter by `org_id`
  - Path parameter IDs validated as UUID type
  - Pydantic schemas for all request bodies

## dashboard.py
- Status: FIXED
- Endpoints: 7
- Issues found: 7
- Issues fixed: 7
- Details:
  - FIXED: All 7 endpoints had NO RBAC permission checks -- added `require_permission("incidents:read")` to all endpoints
  - Tenant isolation was already correct (all queries filter by `org_id`)
  - Query parameters have proper bounds (days: ge=1, le=365)
  - Pydantic response schemas for all endpoints

## webhooks.py
- Status: FIXED
- Endpoints: 8
- Issues found: 4
- Issues fixed: 4
- Details:
  - FIXED: `list_webhooks` had no RBAC -- added `require_permission("alerts:read")`
  - FIXED: `get_webhook` had no RBAC -- added `require_permission("alerts:read")`
  - FIXED: `get_delivery_stats` had no RBAC -- added `require_permission("alerts:read")`
  - FIXED: `list_deliveries` had no RBAC -- added `require_permission("alerts:read")`
  - Write endpoints correctly use `require_admin`
  - Tenant isolation: all queries filter by `org_id`
  - Webhook ownership validated via `_get_webhook_or_404` helper
  - Pagination with proper bounds

## governance.py
- Status: FIXED
- Endpoints: 10
- Issues found: 10
- Issues fixed: 10
- Details:
  - FIXED: All 10 endpoints had NO RBAC permission checks -- added `require_permission("compliance:read")` to all endpoints
  - Endpoints: owasp-compliance, threat-mapping, compliance-matrix, framework-summary, enforcement-timeline, dora-report, dora-classify, dora-timeline, article12-logs, article12-summary
  - Tenant isolation was already correct (all queries filter by `org_id`)
  - Query parameters have proper bounds
  - Pydantic response schemas for all endpoints

## agents.py
- Status: CLEAN
- Endpoints: 5
- Issues found: 0
- Issues fixed: 0
- Details:
  - All endpoints use RBAC permissions (`agents:read`, `agents:write`)
  - Tenant isolation: all queries filter by `org_id`
  - Path parameter IDs validated as UUID type
  - Pydantic schemas for all request bodies

## agent_policies.py
- Status: CLEAN
- Endpoints: 5
- Issues found: 0
- Issues fixed: 0
- Details:
  - All endpoints use RBAC permissions (`agents:read`, `agents:write`)
  - Tenant isolation: all queries filter by `org_id`
  - Pydantic schemas for all request bodies

## compliance.py
- Status: CLEAN
- Endpoints: 7
- Issues found: 0
- Issues fixed: 0
- Details:
  - All endpoints use RBAC permissions (`compliance:read`, `compliance:write`)
  - Tenant isolation: all queries filter by `org_id`
  - Path traversal defense on report download (filename sanitization)
  - Pydantic schemas for all request bodies

## reviews.py
- Status: FIXED
- Endpoints: 5
- Issues found: 4
- Issues fixed: 4
- Details:
  - FIXED: `list_review_items` had no RBAC -- added `require_permission("incidents:read")`
  - FIXED: `get_review_stats` had no RBAC -- added `require_permission("incidents:read")`
  - FIXED: `create_review_item` had no RBAC -- added `require_permission("incidents:write")`
  - FIXED: `escalate_review_item` had no RBAC -- added `require_permission("incidents:write")`
  - `decide_review_item` already had `get_current_user` (reviewer identity tracking)
  - Tenant isolation: all queries filter by `org_id`
  - Status validation on decide (only pending/escalated allowed)

## sandboxes.py
- Status: CLEAN
- Endpoints: 7
- Issues found: 0
- Issues fixed: 0
- Details:
  - All endpoints use RBAC permissions (`sandboxes:read`, `sandboxes:write`)
  - Tenant isolation: all queries filter by `org_id`
  - Pydantic schemas for all request bodies

## red_team.py
- Status: FIXED
- Endpoints: 9
- Issues found: 9
- Issues fixed: 9
- Details:
  - FIXED: All 9 endpoints had NO RBAC -- added `require_permission("detectors:read")` to reads, `require_permission("detectors:write")` to writes
  - `create_run` is expensive (runs detection pipeline) -- now requires `detectors:write` permission
  - Tenant isolation was already correct (all queries filter by `org_id`)
  - Test categories validated against allowlist
  - Pydantic schemas for request bodies

## threat_intel.py
- Status: FIXED
- Endpoints: 6
- Issues found: 6
- Issues fixed: 6
- Details:
  - FIXED: All 6 endpoints had NO RBAC -- added `require_permission("detectors:read")` to reads, `require_permission("detectors:write")` to writes
  - FIXED: `seed_platform_indicators` now requires `require_admin` (creates platform-level org_id=None records)
  - Tenant isolation correct (queries include `org_id == org.id OR org_id IS NULL` for platform indicators)
  - `indicator_type` validated against allowlist

## shadow_ai.py
- Status: FIXED
- Endpoints: 5
- Issues found: 5
- Issues fixed: 5
- Details:
  - FIXED: All 5 endpoints had NO RBAC -- added `require_permission("incidents:read")` to reads, `require_permission("incidents:write")` to writes
  - Tenant isolation was already correct (all queries filter by `org_id`)
  - Status updates validated via regex pattern
  - Pydantic schemas with field constraints

## conversations.py
- Status: FIXED
- Endpoints: 6
- Issues found: 6
- Issues fixed: 6
- Details:
  - FIXED: All 6 endpoints had NO RBAC -- added `require_permission("incidents:read")` to reads, `require_permission("incidents:write")` to writes
  - Tenant isolation was already correct (all queries filter by `org_id`)
  - Risk score clamped to 0-100 range
  - Auto-escalation on critical risk threshold

## traces.py
- Status: FIXED
- Endpoints: 2
- Issues found: 2
- Issues fixed: 2
- Details:
  - FIXED: `list_traces` had no RBAC -- added `require_permission("incidents:read")`
  - FIXED: `get_trace_detail` had no RBAC -- added `require_permission("incidents:read")`
  - Tenant isolation correct (all queries filter by `org_id`)
  - Path parameter `trace_id` validated as UUID type
  - Query params have proper bounds (skip ge=0, limit ge=1 le=200)
  - Pydantic response schemas for all endpoints

## siem.py
- Status: FIXED
- Endpoints: 6
- Issues found: 3
- Issues fixed: 3
- Details:
  - FIXED: `list_siem_formats` had no RBAC -- added `require_permission("alerts:read")`
  - FIXED: `preview_format` had no RBAC -- added `require_permission("alerts:read")`
  - FIXED: `list_siem_destinations` had no RBAC -- added `require_permission("alerts:read")`
  - Write endpoints (create, update, delete) correctly use `require_admin`
  - Tenant isolation correct (all queries filter by `org_id`)
  - Format validated against allowlist
  - Pydantic schemas for all request bodies

## billing.py
- Status: CLEAN
- Endpoints: 4
- Issues found: 0
- Issues fixed: 0
- Details:
  - All user endpoints use RBAC permissions (`billing:read`, `billing:write`)
  - Stripe webhook uses signature verification (no JWT auth -- correct for webhooks)
  - Tenant isolation: org-scoped via `get_current_org`
  - Pydantic schemas for all request bodies

## model_registry.py
- Status: FIXED
- Endpoints: 6
- Issues found: 3
- Issues fixed: 3
- Details:
  - FIXED: `list_models` had no RBAC -- added `require_permission("compliance:read")`
  - FIXED: `get_model_summary` had no RBAC -- added `require_permission("compliance:read")`
  - FIXED: `get_model` had no RBAC -- added `require_permission("compliance:read")`
  - Write endpoints (register, update, delete) correctly use `require_admin`
  - Tenant isolation correct (all queries filter by `org_id`)
  - Path parameter `model_id` validated as UUID type
  - Pydantic schemas for all request bodies

## playground.py
- Status: FIXED
- Endpoints: 2
- Issues found: 2
- Issues fixed: 2
- Details:
  - FIXED: `test_detectors` had no RBAC -- added `require_permission("detectors:read")`
  - FIXED: `list_categories` had no RBAC -- added `require_permission("detectors:read")`
  - Tenant isolation: org passed to detection pipeline
  - Pydantic schemas for request/response bodies

## ingest.py
- Status: CLEAN
- Endpoints: 2
- Issues found: 0
- Issues fixed: 0
- Details:
  - Both endpoints use API key auth via `get_current_org_from_api_key` (correct for SDK ingestion)
  - Tenant isolation: `org.id` set on all created records
  - Pydantic schemas for all request bodies (SDKEvent, TraceSpan batches)
  - No RBAC needed -- SDK endpoints use API key auth, not user roles

## retention.py
- Status: FIXED
- Endpoints: 5
- Issues found: 4
- Issues fixed: 4
- Details:
  - FIXED: `get_retention_policy` had no RBAC -- added `require_permission("settings:read")`
  - FIXED: `list_archives` had no RBAC -- added `require_permission("settings:read")`
  - FIXED: `get_archive` had no RBAC -- added `require_permission("settings:read")`
  - FIXED: `retrieve_archive` used `get_current_user` (no RBAC) -- upgraded to `require_permission("settings:read")`
  - `update_retention_policy` correctly uses `require_admin`
  - Tenant isolation correct (all queries filter by `org_id`)
  - Path parameter `archive_id` validated as UUID type
  - Audit logging on policy update and archive retrieval

## proxy_endpoints.py
- Status: FIXED
- Endpoints: 5
- Issues found: 2
- Issues fixed: 2
- Details:
  - FIXED: `list_proxy_endpoints` had no RBAC -- added `require_permission("settings:read")`
  - FIXED: `get_proxy_endpoint` had no RBAC -- added `require_permission("settings:read")`
  - Write endpoints (create, update, delete) correctly use `require_admin`
  - Rate limiting on create (10/min)
  - Tenant isolation correct (org_id passed to service layer)
  - Path parameter `endpoint_id` validated as UUID type
  - Pydantic schemas for all request bodies

## governance_testing.py
- Status: FIXED
- Endpoints: 8
- Issues found: 8
- Issues fixed: 8
- Details:
  - FIXED: `get_stress_test_suite` had no RBAC -- added `require_permission("detectors:read")`
  - FIXED: `get_readiness_score` had no RBAC -- added `require_permission("detectors:read")`
  - FIXED: `run_stress_test` had no RBAC -- added `require_permission("detectors:write")`
  - FIXED: `get_investigation_summary` had no RBAC -- added `require_permission("incidents:read")`
  - FIXED: `get_investigation` had no RBAC -- added `require_permission("incidents:read")`
  - FIXED: `get_policies` had no RBAC -- added `require_permission("compliance:read")`
  - FIXED: `classify_interaction` had no RBAC -- added `require_permission("compliance:read")`
  - FIXED: `get_policy_compliance` had no RBAC -- added `require_permission("compliance:read")`
  - Tenant isolation correct (all queries filter by `org_id`)
  - Query params have proper bounds (days ge=1 le=365)
  - Pydantic schemas for all request/response bodies

## websocket.py
- Status: CLEAN
- Endpoints: 1
- Issues found: 0
- Issues fixed: 0
- Details:
  - JWT validation via `_authenticate_ws` (verifies token type, user active status, org membership)
  - Tenant isolation: subscribes only to org-specific Redis channel (`org:{org_id}:events`)
  - Proper connection rejection on auth failure (close code 4001)
  - No RBAC needed -- WebSocket event streaming is read-only, user auth is sufficient
  - Redis pub/sub cleanup in finally block (unsubscribe, close)
