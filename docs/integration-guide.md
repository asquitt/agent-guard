# Archived integration guide

> **Mothballed:** AgentGuard is not authorized for standalone deployment or
> provider traffic. This guide is preserved implementation reference only. Do
> not install the SDKs, connect credentials, send provider requests, or incur
> runtime/provider spend unless an explicit reactivation decision satisfies
> every gate in [`PROJECT_STATUS.json`](../PROJECT_STATUS.json).

The archived implementation accepts provider-compatible requests at an
explicit deployment, forwards them through an organization-owned endpoint, and
records available detection evidence. A reactivation verification would use an
explicit deployment origin:

```bash
export AGENTGUARD_BASE_URL=http://localhost:8001
export AGENTGUARD_API_KEY=ag_live_replace_me
```

There is no implied hosted origin. The repository SDKs are source previews and
are not claimed to be published to package registries.

## Prerequisites

Every proxy request needs:

1. An organization API key in `Authorization: Bearer ...`.
2. An active provider endpoint owned by the same organization.
3. A provider credential configured in the AgentGuard deployment.
4. For observable detection, an active detector and any required worker or
   external model dependency.

`X-AgentGuard-Endpoint-Id` is optional. When supplied, it selects that
organization-owned endpoint; otherwise the backend resolves an active endpoint
for the route's provider.

## Python source preview

Install from the repository root:

```bash
python -m pip install -e './sdk/python[openai,anthropic]'
```

### OpenAI

```python
import os

import agentguard
from openai import OpenAI

agentguard_key = os.environ["AGENTGUARD_API_KEY"]
client = OpenAI(api_key=agentguard_key)
client = agentguard.wrap_openai(
    client,
    api_key=agentguard_key,
    base_url=os.environ["AGENTGUARD_BASE_URL"],
    # endpoint_id="organization-owned-endpoint-uuid",
)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.choices[0].message.content)
```

The wrapper base is `/api/v1/proxy/v1`; the OpenAI client appends
`/chat/completions`, producing
`/api/v1/proxy/v1/chat/completions` end to end.
The wrapper uses the official client's `with_options` request configuration and
returns a configured clone; it does not mutate the input client.

Without the wrapper:

```python
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["AGENTGUARD_API_KEY"],
    base_url=f'{os.environ["AGENTGUARD_BASE_URL"]}/api/v1/proxy/v1',
)
```

### Anthropic

```python
import os

import agentguard
from anthropic import Anthropic

agentguard_key = os.environ["AGENTGUARD_API_KEY"]
client = Anthropic(api_key=agentguard_key)
client = agentguard.wrap_anthropic(
    client,
    api_key=agentguard_key,
    base_url=os.environ["AGENTGUARD_BASE_URL"],
)

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=256,
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.content[0].text)
```

The wrapper base is `/api/v1/proxy`; the Anthropic client appends
`/v1/messages`, producing `/api/v1/proxy/v1/messages` end to end.
The same configured-clone contract applies to Anthropic.

Use the wrapper for Anthropic so the organization key is carried in the Bearer
header accepted by the AgentGuard backend. Setting only Anthropic's `api_key`
sends `x-api-key`, which is not the proxy authentication contract.

## Node.js source preview

Build and install from the checkout rather than assuming a registry release:

```bash
cd sdk/node
npm install
npm run build
```

### OpenAI

```typescript
import OpenAI from 'openai';
import { wrapOpenAI } from 'agentguard';

const agentguardKey = process.env.AGENTGUARD_API_KEY!;
const client = wrapOpenAI(new OpenAI({ apiKey: agentguardKey }), {
  apiKey: agentguardKey,
  baseUrl: process.env.AGENTGUARD_BASE_URL!,
});

const response = await client.chat.completions.create({
  model: 'gpt-4o-mini',
  messages: [{ role: 'user', content: 'Hello' }],
});
```

### Anthropic

```typescript
import Anthropic from '@anthropic-ai/sdk';
import { wrapAnthropic } from 'agentguard';

const agentguardKey = process.env.AGENTGUARD_API_KEY!;
const client = wrapAnthropic(new Anthropic({ apiKey: agentguardKey }), {
  apiKey: agentguardKey,
  baseUrl: process.env.AGENTGUARD_BASE_URL!,
});

const response = await client.messages.create({
  model: 'claude-sonnet-4-20250514',
  max_tokens: 256,
  messages: [{ role: 'user', content: 'Hello' }],
});
```

The Node wrappers use the official clients' `withOptions` request
configuration and return configured clones. They attach the AgentGuard Bearer
credential and optional metadata to the actual provider-SDK request.

Framework callbacks in both source previews use in-memory, best-effort event
delivery rather than a durable queue. Automatic delivery failures retain the
batch only while the process lives. Explicit `flush`/`manualFlush` calls surface
HTTP and transport failures so callers can retry; process termination can still
lose buffered events.

## Raw HTTP

OpenAI-compatible chat completion:

```bash
curl --fail-with-body \
  "$AGENTGUARD_BASE_URL/api/v1/proxy/v1/chat/completions" \
  -H "Authorization: Bearer $AGENTGUARD_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello"}]}'
```

Anthropic-compatible message:

```bash
curl --fail-with-body \
  "$AGENTGUARD_BASE_URL/api/v1/proxy/v1/messages" \
  -H "Authorization: Bearer $AGENTGUARD_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"model":"claude-sonnet-4-20250514","max_tokens":256,"messages":[{"role":"user","content":"Hello"}]}'
```

To select an endpoint explicitly, add:

```text
X-AgentGuard-Endpoint-Id: organization-owned-endpoint-uuid
```

## Detection and enforcement semantics

Detector behavior is configuration- and execution-dependent:

| Condition | Current behavior |
| --- | --- |
| No matching active detector | Provider response can pass without an incident |
| Synchronous `monitor` or `warn` result | Incident may be recorded; response passes through |
| Synchronous `redact` result | Non-streaming response may be modified before return |
| Synchronous `block` result | Non-streaming request returns `403` |
| Asynchronous result | Runs after response and cannot retract it |
| Streaming request | Stream is delivered before asynchronous analysis; monitor-only |
| Detection timeout with degraded mode | Response may proceed while work is queued asynchronously |

Do not infer enforcement from an action-mode label alone. Verify a known
trigger against the exact detector configuration and confirm the returned body,
persisted request, organization ownership, and incident.

The current proxy returns an OpenAI-style block body from the shared handler:

```json
{
  "error": {
    "message": "Request blocked by security policy",
    "type": "detection_blocked"
  }
}
```

Provider SDKs surface non-2xx responses through their normal error types. Do
not match human-readable strings as an authorization or policy decision; inspect
the status and structured error payload.

## Persistence and data handling

The backend can retain proxy request and response content and persist incidents
in PostgreSQL. Use synthetic inputs until your deployment's retention,
redaction, encryption, backup, and role boundaries have been independently
validated. Dashboard visibility is separate evidence from provider success.

Compliance categories and framework mappings support review workflows. They do
not prove that a deployment or organization satisfies a regulatory framework.

## Next steps

- [Quick start](./quickstart.md)
- [API reference](./api-reference.md)
