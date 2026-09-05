# AgentGuard Python SDK source preview

> **Archive status:** AgentGuard is mothballed as a standalone product. This
> proprietary SDK is preserved as source reference only; do not publish,
> install, connect it to a provider, or incur runtime/provider spend unless an
> explicit reactivation decision satisfies every gate in
> [`PROJECT_STATUS.json`](../../PROJECT_STATUS.json). The commands and examples
> below are historical verification material, not current operating
> instructions.

This directory contains the archived Python client source. This repository does
not claim that the package is published to a package registry or that a hosted
AgentGuard API exists.

The wrappers route provider SDK calls through one explicit deployment. They do
not guarantee that a detector is configured, that an incident will be created,
or that a response will be blocked.

## Install from the checkout

From the repository root:

```bash
python -m pip install -e './sdk/python[openai,anthropic]'
```

Set the deployment origin and organization API key through your local secret
process:

```bash
export AGENTGUARD_BASE_URL=http://localhost:8001
export AGENTGUARD_API_KEY=ag_live_replace_me
```

## OpenAI

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
```

`wrap_openai` returns a configured client clone with base
`<deployment>/api/v1/proxy/v1`. The OpenAI SDK appends
`/chat/completions`, producing the tracked route
`/api/v1/proxy/v1/chat/completions`.
It uses the official client's `with_options` request configuration and leaves
the input client unchanged.

## Anthropic

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
```

`wrap_anthropic` returns a configured client clone with base
`<deployment>/api/v1/proxy`. The Anthropic SDK appends `/v1/messages`,
producing the tracked route `/api/v1/proxy/v1/messages`.
It uses the same configured-clone contract.

Async OpenAI and Anthropic clients use the same wrappers.

## Wrapper parameters

Both wrappers require:

- `client`: a compatible provider client;
- `api_key`: the organization API key accepted by the AgentGuard proxy;
- `base_url`: the explicit AgentGuard deployment origin.

Optional `endpoint_id` selects one organization-owned provider endpoint.
Optional `metadata` adds `X-AgentGuard-<key>` headers; only send metadata that
your retention and privacy policy permits.

```python
client = agentguard.wrap_openai(
    client,
    api_key=os.environ["AGENTGUARD_API_KEY"],
    base_url=os.environ["AGENTGUARD_BASE_URL"],
    metadata={"session_id": "synthetic-session"},
)
```

## Low-level proxy client

`AgentGuardClient.proxy` and `AsyncAgentGuardClient.proxy` send a provider body
to a tracked proxy path. Always override their deployment base explicitly:

```python
import os

from agentguard import AgentGuardClient

with AgentGuardClient(
    api_key=os.environ["AGENTGUARD_API_KEY"],
    base_url=os.environ["AGENTGUARD_BASE_URL"],
) as client:
    result = client.proxy(
        "/v1/chat/completions",
        {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )
    print(result.data)
```

Management methods such as incident listing use a user access token, not the
organization API key. Supply the access token separately when those methods are
needed:

```python
client = AgentGuardClient(
    api_key=os.environ["AGENTGUARD_API_KEY"],
    access_token=os.environ["AGENTGUARD_ACCESS_TOKEN"],
    base_url=os.environ["AGENTGUARD_BASE_URL"],
)
```

Without `access_token`, management methods fail before sending a request.

## Callback delivery boundary

Framework callback integrations are best-effort, in-memory telemetry helpers;
they are not a durable queue. Automatic flushes do not break the wrapped
workflow on transport or HTTP failure and retain the failed batch only for the
life of that process. Explicit `flush()` or `manual_flush()` raises on a failed
delivery so the caller can retry or record the failure. Process termination can
still lose buffered events.

## Detection boundary

- No active matching detector can mean no incident.
- Only configured synchronous detection can redact or block a non-streaming
  response.
- Streaming data reaches the caller before asynchronous analysis completes and
  must be treated as monitor-only in this revision.
- Provider success does not prove request persistence, worker execution, or
  incident creation.
- Compliance-related findings support review; they are not certification or
  legal advice.

Provider SDKs raise their normal non-2xx errors for proxy failures. Inspect the
HTTP status and structured error body; do not authorize behavior by matching an
error string.

## Verify this source preview

```bash
cd sdk/python
PYTHONPATH=. python -m pytest -q
```

The wrapper tests verify URL construction, including real installed OpenAI and
Anthropic client URL semantics when those optional dependencies are available.
They do not call a provider or prove a deployed detection outcome.

## Repository documentation

- [Quick start](../../docs/quickstart.md)
- [Integration guide](../../docs/integration-guide.md)
- [API reference](../../docs/api-reference.md)
