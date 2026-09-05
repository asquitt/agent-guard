# Archived API reference

> **Mothballed:** This is preserved source reference, not an active service
> contract or authorization to deploy or call AgentGuard. Do not execute these
> routes or incur runtime/provider spend unless an explicit reactivation
> decision satisfies every gate in [`PROJECT_STATUS.json`](../PROJECT_STATUS.json).

This reference describes routes in the archived repository. It is not evidence
of a public deployment. A reactivation verification would set the origin of the
authorized environment explicitly:

```bash
export AGENTGUARD_BASE_URL=http://localhost:8001
```

All paths below are relative to that origin and begin with `/api/v1`.
Development OpenAPI documentation is available at
`$AGENTGUARD_BASE_URL/docs` when enabled by the deployment.

## Authentication boundaries

- Management endpoints use a user access token obtained from the authentication
  flow and enforce role or permission dependencies per route.
- Proxy and ingest endpoints use an organization API key in
  `Authorization: Bearer <key>`.
- `X-AgentGuard-Endpoint-Id` optionally selects an organization-owned proxy
  endpoint. Omitting it asks the backend to resolve an active endpoint for the
  route's provider.

API key scopes and environment labels exist in stored configuration, but this
reference does not claim they authorize individual proxy operations until that
enforcement is independently verified.

## LLM proxy

| Method | Full path | Provider-compatible operation |
| --- | --- | --- |
| `POST` | `/api/v1/proxy/v1/chat/completions` | OpenAI chat completions |
| `POST` | `/api/v1/proxy/v1/completions` | OpenAI legacy completions |
| `POST` | `/api/v1/proxy/v1/embeddings` | OpenAI embeddings |
| `POST` | `/api/v1/proxy/v1/messages` | Anthropic messages |

The request body is forwarded through the configured provider adapter. Common
outcomes include:

| Status | Meaning at this boundary |
| --- | --- |
| `200` | A provider-compatible response was returned |
| `403` | A synchronous detector returned `block` for a non-streaming response |
| `422` | Endpoint selection, provider credential, or request validation failed |
| `429` | A configured rate or usage limit was reached |
| `502` | The upstream provider request failed |
| `503` | The provider circuit breaker rejected the attempt |
| `504` | The upstream provider timed out |

These statuses do not by themselves prove persistence, detector coverage, or
incident creation.

### OpenAI-compatible example

```bash
curl --fail-with-body \
  "$AGENTGUARD_BASE_URL/api/v1/proxy/v1/chat/completions" \
  -H "Authorization: Bearer $AGENTGUARD_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello"}]}'
```

### Anthropic-compatible example

```bash
curl --fail-with-body \
  "$AGENTGUARD_BASE_URL/api/v1/proxy/v1/messages" \
  -H "Authorization: Bearer $AGENTGUARD_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"model":"claude-sonnet-4-20250514","max_tokens":256,"messages":[{"role":"user","content":"Hello"}]}'
```

Streaming is requested with the provider's `stream` field. Streaming content is
returned before asynchronous detection finishes, so it is monitor-only in this
revision.

## Authentication

| Method | Full path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Create a user and organization when deployment enrollment is enabled |
| `POST` | `/api/v1/auth/login` | Return tokens or an MFA challenge |
| `POST` | `/api/v1/auth/refresh` | Rotate a refresh token |
| `POST` | `/api/v1/auth/change-password` | Change password and rotate tokens |
| `GET` | `/api/v1/auth/me` | Return current user and organization |
| `POST` | `/api/v1/auth/logout` | End the current client session contract |

Registration request:

```json
{
  "email": "user@example.test",
  "password": "LocalPassword1!",
  "full_name": "Local User",
  "org_name": "Local Evaluation",
  "controlled_evaluation_accepted": true,
  "access_code": "operator-provided-code"
}
```

Passwords must be 12–128 characters and contain uppercase, lowercase, digit,
and special characters. Registration is disabled unless the deployment
operator sets `REGISTRATION_ENABLED`. Outside the explicit development/test
local bypass, the request also needs the configured access code. A rejected
enrollment returns a generic `403` without revealing gate configuration. Login
may return `mfa_required: true` with an MFA token instead of access and refresh
tokens.

## Organization API keys

| Method | Full path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/api-keys/` | Create an API key; full key is returned once |
| `GET` | `/api/v1/api-keys/` | List key metadata without full keys |
| `PATCH` | `/api/v1/api-keys/{key_id}` | Update key metadata |
| `DELETE` | `/api/v1/api-keys/{key_id}` | Revoke a key |

These management routes require the route's admin dependency. Never place full
keys in repository files, screenshots, logs, or command arguments.

## Proxy endpoints

| Method | Full path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/proxy-endpoints/` | Create an endpoint configuration |
| `GET` | `/api/v1/proxy-endpoints/` | List organization-owned endpoints |
| `GET` | `/api/v1/proxy-endpoints/{endpoint_id}` | Get one endpoint |
| `PATCH` | `/api/v1/proxy-endpoints/{endpoint_id}` | Update one endpoint |
| `DELETE` | `/api/v1/proxy-endpoints/{endpoint_id}` | Delete one endpoint |

OpenAI uses target origin `https://api.openai.com`; the proxy appends the
incoming `/v1/...` path. Anthropic similarly receives the tracked
`/v1/messages` path. Provider credentials are a deployment prerequisite and
must not be embedded in public examples.

## Detectors

| Method | Full path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/detectors/` | Create a detector |
| `GET` | `/api/v1/detectors/` | List detectors |
| `GET` | `/api/v1/detectors/{detector_id}` | Get a detector |
| `PATCH` | `/api/v1/detectors/{detector_id}` | Update a detector |
| `DELETE` | `/api/v1/detectors/{detector_id}` | Delete a detector |
| `POST` | `/api/v1/detectors/{detector_id}/rules` | Add a rule |
| `DELETE` | `/api/v1/detectors/{detector_id}/rules/{rule_id}` | Delete a rule |

Action modes accepted by the schema are `monitor`, `warn`, `redact`, and
`block`. Runtime effect depends on detector category, activation, execution
phase, and outcome. In particular, asynchronous and streaming detection cannot
retract an already delivered response.

## Incidents

| Method | Full path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/incidents/` | List organization-owned incidents |
| `GET` | `/api/v1/incidents/stats` | Aggregate incident counts |
| `GET` | `/api/v1/incidents/{incident_id}` | Get incident detail and actions |
| `PATCH` | `/api/v1/incidents/{incident_id}` | Update incident status |
| `POST` | `/api/v1/incidents/{incident_id}/actions` | Add an incident action |
| `POST` | `/api/v1/incidents/bulk-update` | Update up to 100 incident statuses |

List filters include `skip`, `limit`, `status`, `severity`, `category`,
`detectorId`, `q`, `dateFrom`, and `dateTo`.

An incident is evidence that a configured detector recorded a finding. It is
not proof that the caller's response was blocked, that every request was
analyzed, or that a compliance requirement was satisfied.

## Error shapes

Management errors generally use FastAPI's `detail` field:

```json
{"detail": "error message"}
```

The shared non-streaming block response is currently OpenAI-style for both
provider routes:

```json
{
  "error": {
    "message": "Request blocked by security policy",
    "type": "detection_blocked"
  }
}
```

Consumers should use the HTTP status plus structured fields. Error wording is
not a stable authorization contract.

## Evidence and data boundary

The backend can persist request and response content before or alongside
detection. Use synthetic inputs until retention, redaction, encryption,
organization isolation, backups, and operator access are verified for the
specific deployment. Repository routes and tests do not prove hosted operation,
provider success, durable persistence, regulatory compliance, or customer
outcomes.
