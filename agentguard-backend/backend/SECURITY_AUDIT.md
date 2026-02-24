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
