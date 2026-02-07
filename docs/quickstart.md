# Quick Start

Get AgentGuard monitoring your AI agents in under 5 minutes.

## 1. Create an Account

Sign up at [agentguard.app](https://agentguard.app). You'll get an organization and a default proxy endpoint automatically.

## 2. Get Your API Key

Go to **Settings > API Keys** in the dashboard and create a new key. Copy the key -- it starts with `ag_live_`.

## 3. Install the SDK

```bash
pip install agentguard
```

## 4. Integrate with OpenAI

```python
import openai
import agentguard

client = openai.OpenAI(api_key="sk-...")
client = agentguard.wrap_openai(client, api_key="ag_live_...")

# Use client as normal -- AgentGuard monitors all requests
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

That's it. Every request now flows through AgentGuard's detection pipeline. Hallucinations, PII leaks, compliance violations, cost anomalies, and agent loops are detected automatically.

## 5. Integrate with Anthropic

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

## 6. View Incidents

Open the [AgentGuard Dashboard](https://agentguard.app/dashboard). Incidents appear in real time as detectors flag issues. Each incident includes:

- Severity level (critical, high, medium, low, info)
- Detection category (hallucination, pii_leak, compliance, cost_anomaly, loop)
- The full request/response that triggered it
- Recommended action

## Next Steps

- [Integration Guide](./integration-guide.md) -- Python, Node.js, raw HTTP, and curl examples
- [API Reference](./api-reference.md) -- Full endpoint documentation
