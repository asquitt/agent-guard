# API Reference

## Base URL

```
https://proxy.agentguard.app/api/v1
```

For self-hosted deployments, replace with your own host.

## Authentication

All API requests require a Bearer token in the `Authorization` header.

**Dashboard/management endpoints** use a JWT access token obtained from `/api/v1/auth/login`:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Proxy endpoints** use an AgentGuard API key created in the dashboard:

```
Authorization: Bearer ag_live_abc123...
```

## Endpoints

### LLM Proxy

| Method | Path | Description |
|--------|------|-------------|
| POST | `/proxy/v1/chat/completions` | Proxy OpenAI chat completions |
| POST | `/proxy/v1/completions` | Proxy OpenAI legacy completions |
| POST | `/proxy/v1/embeddings` | Proxy OpenAI embeddings |
| POST | `/proxy/v1/messages` | Proxy Anthropic messages |

All proxy endpoints accept the same request body as the upstream provider. Pass `"stream": true` for streaming responses.

**Optional header:** `X-AgentGuard-Endpoint-Id` -- UUID of a specific proxy endpoint configuration. If omitted, the default endpoint for the provider is used.

**Responses:**
- `200` -- Upstream response (may be modified if a detector redacted content)
- `403` -- Response blocked by detection policy
- `429` -- Monthly request limit exceeded
- `502` -- Upstream provider error
- `504` -- Upstream provider timeout

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register a new user and organization |
| POST | `/auth/login` | Authenticate and receive JWT tokens |
| POST | `/auth/refresh` | Refresh an expired access token |
| POST | `/auth/change-password` | Change password (invalidates all sessions) |
| GET | `/auth/me` | Get current user profile and organization |
| POST | `/auth/logout` | Logout (client discards tokens) |

**POST /auth/register**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "Jane Doe",
  "org_name": "Acme Corp"
}
```

Response `201`:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**POST /auth/login**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

Response `200`:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

Rate limited: 5 requests/minute.

### Incidents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/incidents/` | List incidents (paginated, filterable) |
| GET | `/incidents/stats` | Get aggregate incident statistics |
| GET | `/incidents/:id` | Get incident detail with actions |
| PATCH | `/incidents/:id` | Update incident status |
| POST | `/incidents/:id/actions` | Add an action to an incident |
| POST | `/incidents/bulk-update` | Bulk update incident statuses |

**GET /incidents/**

Query parameters:
- `skip` (int, default 0) -- Pagination offset
- `limit` (int, default 50) -- Page size
- `status` (string) -- Filter by status
- `severity` (string) -- Filter by severity level
- `category` (string) -- Filter by detection category
- `detectorId` (UUID) -- Filter by detector
- `q` (string) -- Search text
- `dateFrom` (datetime) -- Start date filter
- `dateTo` (datetime) -- End date filter

Response `200`:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "PII detected in response",
      "severity": "high",
      "category": "pii_leak",
      "status": "open",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 42
}
```

**PATCH /incidents/:id**

```json
{
  "status": "resolved"
}
```

### Detectors

| Method | Path | Description |
|--------|------|-------------|
| GET | `/detectors/` | List detectors |
| POST | `/detectors/` | Create a detector (admin) |
| GET | `/detectors/:id` | Get detector detail |
| PATCH | `/detectors/:id` | Update a detector (admin) |
| DELETE | `/detectors/:id` | Delete a detector (admin) |
| POST | `/detectors/:id/rules` | Add a rule to a detector (admin) |
| DELETE | `/detectors/:id/rules/:rule_id` | Delete a rule (admin) |

**POST /detectors/**

```json
{
  "name": "PII Scanner",
  "category": "pii_leak",
  "action_mode": "redact",
  "config": {},
  "rules": [
    {
      "name": "SSN Pattern",
      "rule_type": "regex",
      "parameters": {"pattern": "\\d{3}-\\d{2}-\\d{4}"},
      "is_active": true
    }
  ]
}
```

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/metrics` | Get dashboard metrics |

Response `200`:
```json
{
  "total_incidents": 156,
  "open_incidents": 23,
  "incidents_by_status": [
    {"status": "open", "count": 23},
    {"status": "resolved", "count": 133}
  ],
  "incidents_by_severity": [
    {"severity": "critical", "count": 5},
    {"severity": "high", "count": 18}
  ],
  "recent_incidents": []
}
```

### Alerts

| Method | Path | Description |
|--------|------|-------------|
| GET | `/alerts/` | List alerts |
| POST | `/alerts/destinations` | Create alert destination (admin) |
| GET | `/alerts/destinations` | List alert destinations |
| PATCH | `/alerts/destinations/:id` | Update alert destination (admin) |
| DELETE | `/alerts/destinations/:id` | Delete alert destination (admin) |
| POST | `/alerts/destinations/:id/test` | Send test alert (admin) |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/webhooks/` | List webhooks |
| POST | `/webhooks/` | Create webhook (admin) |
| GET | `/webhooks/:id` | Get webhook detail |
| PATCH | `/webhooks/:id` | Update webhook (admin) |
| DELETE | `/webhooks/:id` | Delete webhook (admin) |

**POST /webhooks/**

```json
{
  "name": "Slack Alerts",
  "url": "https://hooks.slack.com/services/...",
  "secret": "whsec_...",
  "event_types": ["incident.created", "incident.resolved"],
  "min_severity": "high"
}
```

### Proxy Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/proxy-endpoints/` | List proxy endpoint configs |
| POST | `/proxy-endpoints/` | Create proxy endpoint (admin) |
| GET | `/proxy-endpoints/:id` | Get proxy endpoint detail |
| PATCH | `/proxy-endpoints/:id` | Update proxy endpoint (admin) |
| DELETE | `/proxy-endpoints/:id` | Delete proxy endpoint (admin) |

### API Keys

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api-keys/` | List API keys |
| POST | `/api-keys/` | Create API key (admin) |
| DELETE | `/api-keys/:id` | Revoke API key (admin) |

## Error Format

All errors return JSON:

```json
{
  "detail": "error message"
}
```

For proxy endpoints, errors match the upstream provider format:

**OpenAI-style:**
```json
{
  "error": {
    "message": "Request blocked by security policy",
    "type": "detection_blocked"
  }
}
```

**Anthropic-style:**
```json
{
  "type": "error",
  "error": {
    "type": "detection_blocked",
    "message": "Request blocked by security policy"
  }
}
```

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `/auth/register` | 5/minute |
| `/auth/login` | 5/minute |
| `/auth/refresh` | 10/minute |
| `/proxy-endpoints/` (POST) | 10/minute |
| Proxy endpoints | Per-plan monthly request limit |

When rate limited, you receive a `429` response.

## Detection Categories

| Category | Key | Description |
|----------|-----|-------------|
| Hallucination | `hallucination` | Factual inconsistency in LLM output |
| PII Leak | `pii_leak` | Personal data exposure in responses |
| Compliance | `compliance` | Regulatory violations (SOX, PCI-DSS, FFIEC) |
| Cost Anomaly | `cost_anomaly` | Unusual token consumption patterns |
| Loop Detection | `loop` | Repeated outputs indicating a stuck agent |

## Severity Levels

From highest to lowest: `critical`, `high`, `medium`, `low`, `info`.

## Action Modes

| Mode | Behavior |
|------|----------|
| `monitor` | Log incident, pass response through unchanged |
| `warn` | Log incident, add warning metadata |
| `redact` | Remove sensitive content from the response before returning |
| `block` | Return 403, do not pass the response to the caller |
