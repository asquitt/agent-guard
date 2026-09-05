# AgentGuard Node.js SDK source preview

> **Archive status:** AgentGuard is mothballed as a standalone product. This
> unlicensed SDK is preserved as source reference only; do not publish, install,
> connect it to a provider, or incur runtime/provider spend unless an explicit
> reactivation decision satisfies every gate in
> [`PROJECT_STATUS.json`](../../PROJECT_STATUS.json). The commands and examples
> below are historical verification material, not current operating
> instructions.

This directory contains the archived Node.js client source. This repository
does not claim that the package is published to npm or that a hosted AgentGuard
API exists.

## Build from the checkout

```bash
cd sdk/node
npm install
npm run build
```

A consuming local project can install the built checkout with a filesystem
dependency such as `npm install ./sdk/node`. Always provide the deployment
origin explicitly:

```bash
export AGENTGUARD_BASE_URL=http://localhost:8001
export AGENTGUARD_API_KEY=ag_live_replace_me
```

## OpenAI

```typescript
import OpenAI from 'openai';
import { wrapOpenAI } from 'agentguard';

const agentguardKey = process.env.AGENTGUARD_API_KEY!;
const client = wrapOpenAI(new OpenAI({ apiKey: agentguardKey }), {
  apiKey: agentguardKey,
  baseUrl: process.env.AGENTGUARD_BASE_URL!,
  // endpointId: 'organization-owned-endpoint-uuid',
});

const response = await client.chat.completions.create({
  model: 'gpt-4o-mini',
  messages: [{ role: 'user', content: 'Hello' }],
});
```

The wrapper base is `<deployment>/api/v1/proxy/v1`; the OpenAI client appends
`/chat/completions` to reach `/api/v1/proxy/v1/chat/completions`.
It uses the official client's `withOptions` request configuration and returns a
configured clone; the input client is unchanged.

## Anthropic

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

The wrapper base is `<deployment>/api/v1/proxy`; the Anthropic client appends
`/v1/messages` to reach `/api/v1/proxy/v1/messages`.
It uses the same configured-clone contract.

## Metadata and endpoint selection

```typescript
const client = wrapOpenAI(openaiClient, {
  apiKey: process.env.AGENTGUARD_API_KEY!,
  baseUrl: process.env.AGENTGUARD_BASE_URL!,
  endpointId: 'organization-owned-endpoint-uuid',
  metadata: { sessionId: 'synthetic-session' },
});
```

Metadata becomes `X-AgentGuard-<key>` headers. Only send values that your
retention and privacy policy permits.

## Low-level proxy client

```typescript
import { AgentGuardClient } from 'agentguard';

const client = new AgentGuardClient({
  apiKey: process.env.AGENTGUARD_API_KEY!,
  baseUrl: process.env.AGENTGUARD_BASE_URL!,
});

const result = await client.proxy('/v1/chat/completions', {
  model: 'gpt-4o-mini',
  messages: [{ role: 'user', content: 'Hello' }],
});
console.log(result.data);
```

Management methods such as incident listing use a user access token, not the
organization API key. Configure it separately only when those methods are
needed:

```typescript
const client = new AgentGuardClient({
  apiKey: process.env.AGENTGUARD_API_KEY!,
  accessToken: process.env.AGENTGUARD_ACCESS_TOKEN!,
  baseUrl: process.env.AGENTGUARD_BASE_URL!,
});
```

Without `accessToken`, management methods fail before sending a request.

## Callback delivery boundary

Framework callback integrations are best-effort, in-memory telemetry helpers;
they are not a durable queue. Automatic flushes do not break the wrapped
workflow on transport or HTTP failure and retain the failed batch only for the
life of that process. Explicit `manualFlush()` rejects on a failed delivery so
the caller can retry or record the failure. Process termination can still lose
buffered events.

## Detection boundary

- Wrapping a client does not activate a detector or prove incident creation.
- Only configured synchronous detection can redact or block a non-streaming
  response.
- Streaming is delivered before asynchronous analysis completes and is
  monitor-only in this revision.
- Provider success does not prove persistence, worker execution, or a customer
  outcome.
- Compliance-related findings are review aids, not certification or legal
  advice.

## Verify this source preview

```bash
cd sdk/node
npm run typecheck
npm test
```

These tests verify wrapper configuration and tracked route construction. They
do not call a provider or prove deployed detection behavior.

## Repository documentation

- [Quick start](../../docs/quickstart.md)
- [Integration guide](../../docs/integration-guide.md)
- [API reference](../../docs/api-reference.md)
