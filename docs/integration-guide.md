# Integration Guide

AgentGuard works as an LLM proxy. Your application sends requests to AgentGuard instead of directly to OpenAI/Anthropic. AgentGuard forwards them upstream, runs detection on the responses, and returns the result. No code changes beyond swapping the base URL.

## Authentication

Every request to the proxy requires two things:

1. **API Key** -- passed in the `Authorization` header as `Bearer ag_live_...`
2. **Endpoint ID** (optional) -- passed in the `X-AgentGuard-Endpoint-Id` header. If omitted, the default endpoint for the provider is used.

```
Authorization: Bearer ag_live_abc123...
X-AgentGuard-Endpoint-Id: 550e8400-e29b-41d4-a716-446655440000
```

## Python -- OpenAI SDK

The SDK wraps the OpenAI client to route traffic through AgentGuard automatically.

```python
import openai
import agentguard

client = openai.OpenAI(api_key="sk-...")
client = agentguard.wrap_openai(client, api_key="ag_live_...")

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Summarize our Q3 earnings."}]
)
print(response.choices[0].message.content)
```

### Manual base_url override (no SDK)

```python
import openai

client = openai.OpenAI(
    api_key="ag_live_...",  # AgentGuard API key
    base_url="https://proxy.agentguard.app/api/v1/proxy"
)

# The client thinks it's talking to OpenAI, but traffic routes through AgentGuard
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

> Your upstream OpenAI key is stored in the proxy endpoint configuration in the dashboard. AgentGuard injects it before forwarding.

## Python -- Anthropic SDK

```python
import anthropic
import agentguard

client = anthropic.Anthropic(api_key="sk-ant-...")
client = agentguard.wrap_anthropic(client, api_key="ag_live_...")

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Draft a compliance report."}]
)
print(response.content[0].text)
```

## Python -- Raw httpx/requests

If you don't use an SDK, POST directly to the proxy endpoint.

### OpenAI-compatible request

```python
import httpx

response = httpx.post(
    "https://proxy.agentguard.app/api/v1/proxy/v1/chat/completions",
    headers={
        "Authorization": "Bearer ag_live_...",
        "Content-Type": "application/json",
    },
    json={
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello!"}]
    },
    timeout=120.0,
)
print(response.json())
```

### Anthropic-compatible request

```python
import httpx

response = httpx.post(
    "https://proxy.agentguard.app/api/v1/proxy/v1/messages",
    headers={
        "Authorization": "Bearer ag_live_...",
        "Content-Type": "application/json",
    },
    json={
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": "Hello!"}]
    },
    timeout=120.0,
)
print(response.json())
```

## Node.js -- OpenAI SDK

Point the OpenAI client's `baseURL` at AgentGuard.

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "ag_live_...",  // AgentGuard API key
  baseURL: "https://proxy.agentguard.app/api/v1/proxy",
});

const response = await client.chat.completions.create({
  model: "gpt-4",
  messages: [{ role: "user", content: "Hello!" }],
});

console.log(response.choices[0].message.content);
```

## Node.js -- Anthropic SDK

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({
  apiKey: "ag_live_...",  // AgentGuard API key
  baseURL: "https://proxy.agentguard.app/api/v1/proxy",
});

const response = await client.messages.create({
  model: "claude-sonnet-4-20250514",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Hello!" }],
});

console.log(response.content[0].text);
```

## curl

### OpenAI proxy

```bash
curl -X POST https://proxy.agentguard.app/api/v1/proxy/v1/chat/completions \
  -H "Authorization: Bearer ag_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Anthropic proxy

```bash
curl -X POST https://proxy.agentguard.app/api/v1/proxy/v1/messages \
  -H "Authorization: Bearer ag_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### With endpoint ID

```bash
curl -X POST https://proxy.agentguard.app/api/v1/proxy/v1/chat/completions \
  -H "Authorization: Bearer ag_live_..." \
  -H "X-AgentGuard-Endpoint-Id: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Streaming

Streaming works transparently. Set `"stream": true` in the request body and AgentGuard will pass through SSE events from the upstream provider. Async detectors run after the stream completes.

```python
# OpenAI streaming
stream = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

## Configuring Detectors

Detectors are configured in the AgentGuard dashboard under **Settings > Detectors**. Five detection categories are available:

| Category | What it detects |
|----------|----------------|
| `hallucination` | Factual inconsistencies in LLM output |
| `pii_leak` | Personal data exposure (SSN, email, phone, etc.) |
| `compliance` | Regulatory violations (SOX, PCI-DSS, FFIEC) |
| `cost_anomaly` | Unusual token consumption patterns |
| `loop` | Repeated outputs indicating a stuck agent |

Each detector has an **action mode** that controls what happens when a detection fires:

| Mode | Behavior |
|------|----------|
| `monitor` | Log the incident, pass the response through |
| `warn` | Log the incident, add a warning header |
| `redact` | Redact sensitive content from the response |
| `block` | Block the response entirely (returns 403) |

## Handling Blocked Responses

When a detector blocks a response, you'll receive a `403` with this format:

**OpenAI proxy:**
```json
{
  "error": {
    "message": "Request blocked by security policy",
    "type": "detection_blocked"
  }
}
```

**Anthropic proxy:**
```json
{
  "type": "error",
  "error": {
    "type": "detection_blocked",
    "message": "Request blocked by security policy"
  }
}
```

Handle this in your application:

```python
from openai import OpenAIError

try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "..."}]
    )
except OpenAIError as e:
    if "detection_blocked" in str(e):
        print("Response blocked by AgentGuard security policy")
    else:
        raise
```

## Next Steps

- [API Reference](./api-reference.md) -- Full endpoint documentation
- [Quick Start](./quickstart.md) -- 5-minute setup
