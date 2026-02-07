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

## API Reference

### `agentguard.wrap_openai(client, api_key, **kwargs)`

Wraps an OpenAI client to route all requests through AgentGuard.

**Parameters:**
- `client` -- An `openai.OpenAI` instance
- `api_key` (str) -- Your AgentGuard API key (`ag_live_...`)
- `base_url` (str, optional) -- Custom AgentGuard proxy URL. Defaults to `https://proxy.agentguard.app/api/v1/proxy`
- `endpoint_id` (str, optional) -- UUID of a specific proxy endpoint configuration

**Returns:** The wrapped OpenAI client. Use it exactly as you would a normal OpenAI client.

### `agentguard.wrap_anthropic(client, api_key, **kwargs)`

Wraps an Anthropic client to route all requests through AgentGuard.

**Parameters:**
- `client` -- An `anthropic.Anthropic` instance
- `api_key` (str) -- Your AgentGuard API key (`ag_live_...`)
- `base_url` (str, optional) -- Custom AgentGuard proxy URL
- `endpoint_id` (str, optional) -- UUID of a specific proxy endpoint configuration

**Returns:** The wrapped Anthropic client.

### `agentguard.AgentGuardClient(api_key, base_url=None)`

Low-level client for direct API access.

```python
from agentguard import AgentGuardClient

ag = AgentGuardClient(api_key="ag_live_...")

# List incidents
incidents = ag.incidents.list(severity="high", status="open")

# Get incident detail
incident = ag.incidents.get("incident-uuid")

# Update incident status
ag.incidents.update("incident-uuid", status="resolved")

# List detectors
detectors = ag.detectors.list()

# Get dashboard metrics
metrics = ag.dashboard.metrics()
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
