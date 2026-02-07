# AgentGuard Python SDK

AI agent security monitoring for financial services. Detect hallucinations, PII leaks, compliance violations, cost anomalies, and agent loops in real time.

## Installation

```bash
pip install agentguard
```

## Quick Start

### OpenAI

```python
import openai
import agentguard

client = openai.OpenAI(api_key="sk-...")
client = agentguard.wrap_openai(client, api_key="ag_live_...")

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Anthropic

```python
import anthropic
import agentguard

client = anthropic.Anthropic(api_key="sk-ant-...")
client = agentguard.wrap_anthropic(client, api_key="ag_live_...")

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Custom Metadata

Attach metadata headers to every proxied request for tracing and analytics:

```python
client = agentguard.wrap_openai(
    client,
    api_key="ag_live_...",
    metadata={
        "user_id": "u_123",
        "session_id": "sess_456",
        "agent_name": "support-bot",
    },
)
```

### Async Support

```python
from agentguard import AsyncAgentGuardClient

async with AsyncAgentGuardClient(api_key="ag_live_...") as ag:
    incidents = await ag.list_incidents(severity="high")
```

Async OpenAI/Anthropic clients work with `wrap_openai` / `wrap_anthropic` unchanged.

## API Reference

### `agentguard.wrap_openai(client, api_key, **kwargs)`

Wraps an OpenAI client to route all requests through AgentGuard.

**Parameters:**
- `client` -- An `openai.OpenAI` or `openai.AsyncOpenAI` instance
- `api_key` (str) -- Your AgentGuard API key (`ag_live_...`)
- `base_url` (str, optional) -- Custom AgentGuard proxy URL
- `endpoint_id` (str, optional) -- UUID of a specific proxy endpoint configuration
- `metadata` (dict, optional) -- Key-value pairs sent as `X-AgentGuard-*` headers

**Returns:** The wrapped client.

### `agentguard.wrap_anthropic(client, api_key, **kwargs)`

Wraps an Anthropic client to route all requests through AgentGuard.

**Parameters:**
- `client` -- An `anthropic.Anthropic` or `anthropic.AsyncAnthropic` instance
- `api_key` (str) -- Your AgentGuard API key (`ag_live_...`)
- `base_url` (str, optional) -- Custom AgentGuard proxy URL
- `endpoint_id` (str, optional) -- UUID of a specific proxy endpoint configuration
- `metadata` (dict, optional) -- Key-value pairs sent as `X-AgentGuard-*` headers

**Returns:** The wrapped client.

### `AgentGuardClient` / `AsyncAgentGuardClient`

Low-level clients for direct API access (sync and async).

```python
from agentguard import AgentGuardClient

with AgentGuardClient(api_key="ag_live_...") as ag:
    incidents = ag.list_incidents(severity="high", status="open")
    incident = ag.get_incident("incident-uuid")
```

## Streaming

Streaming works transparently. AgentGuard passes through SSE events and runs async detection after the stream completes.

```python
stream = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

## Handling Blocked Responses

When a detector blocks a response, the proxy returns a 403. The OpenAI/Anthropic SDK will raise an error.

```python
from openai import OpenAIError

try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "..."}]
    )
except OpenAIError as e:
    if "detection_blocked" in str(e):
        print("Blocked by AgentGuard security policy")
    else:
        raise
```

## Documentation

- [Quick Start](https://docs.agentguard.app/quickstart)
- [Integration Guide](https://docs.agentguard.app/integration-guide)
- [API Reference](https://docs.agentguard.app/api-reference)
