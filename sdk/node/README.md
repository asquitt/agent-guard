# AgentGuard Node.js SDK

AI agent security monitoring for financial services. Detect hallucinations, PII leaks, compliance violations, cost anomalies, and agent loops in real time.

## Installation

```bash
npm install agentguard
```

## Quick Start

### OpenAI

```typescript
import OpenAI from 'openai';
import { wrapOpenAI } from 'agentguard';

const client = new OpenAI({ apiKey: 'sk-...' });
const wrapped = wrapOpenAI(client, { apiKey: 'ag_live_...' });

const response = await wrapped.chat.completions.create({
  model: 'gpt-4',
  messages: [{ role: 'user', content: 'Hello!' }],
});
```

### Anthropic

```typescript
import Anthropic from '@anthropic-ai/sdk';
import { wrapAnthropic } from 'agentguard';

const client = new Anthropic({ apiKey: 'sk-ant-...' });
const wrapped = wrapAnthropic(client, { apiKey: 'ag_live_...' });

const response = await wrapped.messages.create({
  model: 'claude-sonnet-4-20250514',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Hello!' }],
});
```

### Custom Metadata

Attach metadata headers for tracing and analytics:

```typescript
const wrapped = wrapOpenAI(client, {
  apiKey: 'ag_live_...',
  metadata: {
    userId: 'u_123',
    sessionId: 'sess_456',
    agentName: 'support-bot',
  },
});
```

### Direct API Client

```typescript
import { AgentGuardClient } from 'agentguard';

const ag = new AgentGuardClient({ apiKey: 'ag_live_...' });

const incidents = await ag.listIncidents({ severity: 'high', status: 'open' });
const incident = await ag.getIncident('incident-uuid');
```

## Documentation

- [Quick Start](https://docs.agentguard.app/quickstart)
- [Integration Guide](https://docs.agentguard.app/integration-guide)
- [API Reference](https://docs.agentguard.app/api-reference)
