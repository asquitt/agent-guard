'use client';

import { useState } from 'react';
import {
  Rocket,
  FileCode,
  Package,
  Terminal,
  Shield,
  Zap,
} from 'lucide-react';

const TABS = [
  { id: 'quickstart', label: 'Quick Start', icon: Rocket },
  { id: 'api', label: 'API Reference', icon: FileCode },
  { id: 'python', label: 'Python SDK', icon: Terminal },
  { id: 'node', label: 'Node.js SDK', icon: Package },
  { id: 'langchain', label: 'LangChain', icon: Zap },
  { id: 'security', label: 'Security', icon: Shield },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function DocsPage() {
  const [tab, setTab] = useState<TabId>('quickstart');

  return (
    <section className="px-6 py-16">
      <div className="mx-auto max-w-5xl">
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Documentation
          </h1>
          <p className="mt-3 text-lg text-muted-foreground">
            Everything you need to integrate AgentGuard into your AI stack.
          </p>
        </div>

        {/* Tab nav */}
        <div className="mb-8 flex flex-wrap gap-2 border-b border-border pb-2">
          {TABS.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-1.5 rounded-t-md px-3 py-2 text-sm font-medium transition-colors ${
                  tab === t.id
                    ? 'border-b-2 border-primary text-primary'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon className="h-4 w-4" />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        <div className="prose-sm max-w-none">
          {tab === 'quickstart' && <QuickStart />}
          {tab === 'api' && <ApiReference />}
          {tab === 'python' && <PythonSDK />}
          {tab === 'node' && <NodeSDK />}
          {tab === 'langchain' && <LangChainIntegration />}
          {tab === 'security' && <SecurityDocs />}
        </div>
      </div>
    </section>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-10">
      <h2 className="mb-4 text-xl font-bold text-foreground">{title}</h2>
      {children}
    </div>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 text-sm leading-relaxed text-muted-foreground">{children}</p>;
}

function Code({ children, lang }: { children: string; lang?: string }) {
  return (
    <div className="mb-4">
      {lang && (
        <div className="rounded-t-lg border border-b-0 border-border bg-muted px-3 py-1 text-[10px] font-medium uppercase text-muted-foreground">
          {lang}
        </div>
      )}
      <pre className={`overflow-x-auto ${lang ? 'rounded-b-lg rounded-t-none' : 'rounded-lg'} border border-border bg-muted/50 p-4 font-mono text-xs text-foreground`}>
        {children}
      </pre>
    </div>
  );
}

function Endpoint({
  method,
  path,
  desc,
  auth,
}: {
  method: string;
  path: string;
  desc: string;
  auth?: string;
}) {
  const methodColors: Record<string, string> = {
    GET: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    POST: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    PATCH: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    DELETE: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    PUT: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  };

  return (
    <div className="mb-2 flex items-start gap-3 rounded-lg border border-border p-3">
      <span className={`shrink-0 rounded px-2 py-0.5 font-mono text-[10px] font-bold ${methodColors[method] ?? ''}`}>
        {method}
      </span>
      <div className="min-w-0 flex-1">
        <code className="text-xs font-medium text-foreground">{path}</code>
        <p className="mt-0.5 text-xs text-muted-foreground">{desc}</p>
        {auth && <span className="text-[10px] text-muted-foreground/70">{auth}</span>}
      </div>
    </div>
  );
}

function QuickStart() {
  return (
    <>
      <Section title="1. Create an Account">
        <P>
          Sign up at the AgentGuard dashboard. You will be guided through creating your first
          proxy endpoint and API key during the onboarding wizard.
        </P>
      </Section>

      <Section title="2. Install the SDK">
        <Code lang="bash">{`# Python
pip install agentguard

# Node.js
npm install @agentguard/sdk`}</Code>
      </Section>

      <Section title="3. Route LLM Traffic Through the Proxy">
        <P>
          Replace your direct OpenAI/Anthropic API calls with the AgentGuard proxy.
          All requests are analyzed in real-time for PII leaks, prompt injection,
          hallucination, compliance violations, and cost anomalies.
        </P>
        <Code lang="python">{`from agentguard import AgentGuardClient

client = AgentGuardClient(
    api_key="ag_live_...",
    endpoint_id="your-endpoint-id",
)

# Works exactly like the OpenAI API
response = client.proxy({
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Summarize our Q4 financials"}],
})
print(response.choices[0].message.content)`}</Code>
      </Section>

      <Section title="4. View Detections in the Dashboard">
        <P>
          Every proxied request is analyzed by 6 detection categories. When a threat is
          detected, an incident is created automatically. View incidents, configure alert
          destinations (Slack, PagerDuty, webhooks), and manage detector sensitivity from
          the dashboard.
        </P>
      </Section>

      <Section title="5. Configure Detectors">
        <P>
          AgentGuard ships with 6 detection categories enabled by default:
          PII Leak Detection, Prompt Injection Detection, Hallucination Detection,
          Compliance Violation Detection, Cost Anomaly Detection, and Loop Detection.
          Each can be individually tuned for sensitivity and action mode (monitor, warn, block).
        </P>
      </Section>
    </>
  );
}

function ApiReference() {
  return (
    <>
      <Section title="Authentication">
        <P>
          All API requests require a Bearer token. Obtain tokens via the login endpoint
          or use an API key for programmatic access.
        </P>
        <Code lang="bash">{`curl -H "Authorization: Bearer <token>" \\
  https://api.agentguard.app/api/v1/incidents`}</Code>

        <h3 className="mb-3 mt-6 text-base font-semibold text-foreground">Auth Endpoints</h3>
        <Endpoint method="POST" path="/api/v1/auth/register" desc="Create account and organization" />
        <Endpoint method="POST" path="/api/v1/auth/login" desc="Authenticate and receive tokens" />
        <Endpoint method="POST" path="/api/v1/auth/refresh" desc="Refresh access token" />
        <Endpoint method="POST" path="/api/v1/auth/forgot-password" desc="Request password reset email" />
        <Endpoint method="POST" path="/api/v1/auth/reset-password" desc="Reset password with token" />
        <Endpoint method="GET" path="/api/v1/auth/me" desc="Get current user profile" auth="Bearer token" />
      </Section>

      <Section title="LLM Proxy">
        <Endpoint method="POST" path="/api/v1/proxy/chat/completions" desc="Proxy an LLM request through AgentGuard" auth="API Key" />
        <P>
          Accepts the standard OpenAI chat completions format. Automatically routes to the
          configured provider and runs all enabled detectors in real-time.
        </P>
      </Section>

      <Section title="Incidents">
        <Endpoint method="GET" path="/api/v1/incidents" desc="List incidents with filtering" auth="Bearer token" />
        <Endpoint method="GET" path="/api/v1/incidents/:id" desc="Get incident details" auth="Bearer token" />
        <Endpoint method="PATCH" path="/api/v1/incidents/:id/status" desc="Update incident status" auth="Bearer token" />
        <Endpoint method="POST" path="/api/v1/incidents/:id/actions" desc="Add remediation action" auth="Bearer token" />
        <Endpoint method="POST" path="/api/v1/incidents/bulk-status" desc="Bulk update incident statuses" auth="Bearer token" />
      </Section>

      <Section title="Detectors">
        <Endpoint method="GET" path="/api/v1/detectors" desc="List configured detectors" auth="Bearer token" />
        <Endpoint method="POST" path="/api/v1/detectors" desc="Create a new detector" auth="Admin" />
        <Endpoint method="PATCH" path="/api/v1/detectors/:id" desc="Update detector settings" auth="Admin" />
        <Endpoint method="DELETE" path="/api/v1/detectors/:id" desc="Delete detector" auth="Admin" />
      </Section>

      <Section title="Agents">
        <Endpoint method="GET" path="/api/v1/agents" desc="List registered AI agents" auth="Bearer token" />
        <Endpoint method="POST" path="/api/v1/agents" desc="Register a new agent" auth="Admin" />
        <Endpoint method="PATCH" path="/api/v1/agents/:id" desc="Update agent metadata" auth="Admin" />
        <Endpoint method="DELETE" path="/api/v1/agents/:id" desc="Delete agent" auth="Admin" />
      </Section>

      <Section title="Model Registry">
        <Endpoint method="GET" path="/api/v1/model-registry" desc="List registered AI models" auth="Bearer token" />
        <Endpoint method="GET" path="/api/v1/model-registry/summary" desc="Model registry summary stats" auth="Bearer token" />
        <Endpoint method="POST" path="/api/v1/model-registry" desc="Register a new model" auth="Admin" />
        <Endpoint method="PATCH" path="/api/v1/model-registry/:id" desc="Update model metadata" auth="Admin" />
        <Endpoint method="DELETE" path="/api/v1/model-registry/:id" desc="Delete model" auth="Admin" />
      </Section>

      <Section title="Alerts & Destinations">
        <Endpoint method="GET" path="/api/v1/alerts/destinations" desc="List alert destinations" auth="Bearer token" />
        <Endpoint method="POST" path="/api/v1/alerts/destinations" desc="Create alert destination (Slack, PagerDuty, webhook)" auth="Admin" />
        <Endpoint method="POST" path="/api/v1/alerts/destinations/:id/test" desc="Test a destination" auth="Admin" />
        <Endpoint method="DELETE" path="/api/v1/alerts/destinations/:id" desc="Delete destination" auth="Admin" />
      </Section>

      <Section title="Compliance">
        <Endpoint method="GET" path="/api/v1/compliance/audit-logs" desc="List audit logs" auth="Bearer token" />
        <Endpoint method="GET" path="/api/v1/compliance/audit-logs/verify" desc="Verify audit chain integrity" auth="Bearer token" />
        <Endpoint method="POST" path="/api/v1/compliance/reports" desc="Generate compliance report" auth="Admin" />
        <Endpoint method="GET" path="/api/v1/compliance/reports" desc="List generated reports" auth="Bearer token" />
      </Section>

      <Section title="Red Team">
        <Endpoint method="GET" path="/api/v1/red-team/runs" desc="List red team test runs" auth="Bearer token" />
        <Endpoint method="POST" path="/api/v1/red-team/runs" desc="Create automated red team run" auth="Admin" />
        <Endpoint method="GET" path="/api/v1/red-team/runs/:id" desc="Get run details with findings" auth="Bearer token" />
        <Endpoint method="GET" path="/api/v1/red-team/stats" desc="Red team summary statistics" auth="Bearer token" />
      </Section>

      <Section title="Webhooks">
        <Endpoint method="GET" path="/api/v1/webhooks" desc="List webhook configurations" auth="Bearer token" />
        <Endpoint method="POST" path="/api/v1/webhooks" desc="Register webhook endpoint" auth="Admin" />
        <Endpoint method="DELETE" path="/api/v1/webhooks/:id" desc="Delete webhook" auth="Admin" />
      </Section>
    </>
  );
}

function PythonSDK() {
  return (
    <>
      <Section title="Installation">
        <Code lang="bash">pip install agentguard</Code>
      </Section>

      <Section title="Basic Usage">
        <Code lang="python">{`from agentguard import AgentGuardClient

client = AgentGuardClient(
    api_key="ag_live_...",
    base_url="https://api.agentguard.app",  # optional
    endpoint_id="your-endpoint-uuid",
    max_retries=3,  # auto-retry on 429/5xx
)

# Proxy a chat completion
response = client.proxy({
    "model": "gpt-4o",
    "messages": [
        {"role": "system", "content": "You are a financial advisor."},
        {"role": "user", "content": "What were our Q4 revenue figures?"},
    ],
})

# Response includes detection results
print(response.choices[0].message.content)
print(response.agentguard_detections)  # List of detection results`}</Code>
      </Section>

      <Section title="Listing Incidents">
        <Code lang="python">{`# List recent incidents
incidents = client.list_incidents(severity="critical", limit=10)
for inc in incidents.items:
    print(f"{inc.title} — {inc.severity} — {inc.status}")`}</Code>
      </Section>

      <Section title="Async Client">
        <Code lang="python">{`from agentguard import AsyncAgentGuardClient

async_client = AsyncAgentGuardClient(api_key="ag_live_...")

response = await async_client.proxy({
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}],
})`}</Code>
      </Section>

      <Section title="Error Handling">
        <Code lang="python">{`from agentguard import (
    AgentGuardError,
    AuthenticationError,
    DetectionBlockedError,
    RateLimitError,
)

try:
    response = client.proxy(payload)
except DetectionBlockedError as e:
    print(f"Request blocked: {e.detection_type} — {e.message}")
except RateLimitError:
    print("Rate limited — retry after backoff")
except AuthenticationError:
    print("Invalid or expired API key")
except AgentGuardError as e:
    print(f"Unexpected error: {e}")`}</Code>
      </Section>

      <Section title="OpenAI Wrapper">
        <P>
          Drop-in replacement that automatically routes through AgentGuard:
        </P>
        <Code lang="python">{`from openai import OpenAI
from agentguard import wrapOpenAI

openai_client = OpenAI()
guarded = wrapOpenAI(openai_client, api_key="ag_live_...", endpoint_id="...")

# Use exactly like OpenAI — all requests go through AgentGuard
response = guarded.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)`}</Code>
      </Section>
    </>
  );
}

function NodeSDK() {
  return (
    <>
      <Section title="Installation">
        <Code lang="bash">npm install @agentguard/sdk</Code>
      </Section>

      <Section title="Basic Usage">
        <Code lang="typescript">{`import { AgentGuardClient } from '@agentguard/sdk';

const client = new AgentGuardClient({
  apiKey: 'ag_live_...',
  endpointId: 'your-endpoint-uuid',
  maxRetries: 3,
});

const response = await client.proxy({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Hello, world!' }],
});

console.log(response.choices[0].message.content);`}</Code>
      </Section>

      <Section title="Error Handling">
        <Code lang="typescript">{`import {
  AgentGuardError,
  DetectionBlockedError,
  RateLimitError,
  AuthenticationError,
} from '@agentguard/sdk';

try {
  const response = await client.proxy(payload);
} catch (err) {
  if (err instanceof DetectionBlockedError) {
    console.log(\`Blocked: \${err.detectionType} — \${err.message}\`);
  } else if (err instanceof RateLimitError) {
    console.log('Rate limited — will retry automatically');
  } else if (err instanceof AuthenticationError) {
    console.log('Invalid API key');
  }
}`}</Code>
      </Section>

      <Section title="OpenAI Wrapper">
        <Code lang="typescript">{`import OpenAI from 'openai';
import { wrapOpenAI } from '@agentguard/sdk';

const openai = new OpenAI();
const guarded = wrapOpenAI(openai, {
  apiKey: 'ag_live_...',
  endpointId: '...',
});

// Use exactly like OpenAI
const response = await guarded.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Hello' }],
});`}</Code>
      </Section>
    </>
  );
}

function LangChainIntegration() {
  return (
    <>
      <Section title="Python — LangChain Callback Handler">
        <P>
          Capture all LLM calls, chain runs, tool invocations, and agent actions.
          Events are buffered and flushed automatically.
        </P>
        <Code lang="python">{`from langchain_openai import ChatOpenAI
from agentguard.integrations.langchain import AgentGuardCallbackHandler

handler = AgentGuardCallbackHandler(
    api_key="ag_live_...",
    endpoint_id="your-endpoint-uuid",
    metadata={"env": "production", "team": "trading"},
)

llm = ChatOpenAI(model="gpt-4o", callbacks=[handler])

# All LLM calls are automatically sent to AgentGuard
response = llm.invoke("Summarize our Q4 financials")

# Or use with agents
from langchain.agents import AgentExecutor
agent = AgentExecutor(agent=..., tools=[...], callbacks=[handler])
agent.invoke({"input": "Check portfolio risk"})`}</Code>
      </Section>

      <Section title="Python — LlamaIndex Integration">
        <Code lang="python">{`from agentguard.integrations.llamaindex import AgentGuardCallbackHandler

handler = AgentGuardCallbackHandler(api_key="ag_live_...")

# Set as global handler
import llama_index.core
llama_index.core.global_handler = handler`}</Code>
      </Section>

      <Section title="Python — OpenTelemetry Exporter">
        <Code lang="python">{`from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from agentguard.integrations.otel import AgentGuardSpanExporter

exporter = AgentGuardSpanExporter(api_key="ag_live_...")
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(exporter))

# All traces are exported to AgentGuard`}</Code>
      </Section>

      <Section title="Node.js — LangChain.js Callback Handler">
        <Code lang="typescript">{`import { ChatOpenAI } from '@langchain/openai';
import { AgentGuardCallbackHandler } from '@agentguard/sdk';

const handler = new AgentGuardCallbackHandler({
  apiKey: 'ag_live_...',
  endpointId: 'your-endpoint-uuid',
});

const llm = new ChatOpenAI({
  model: 'gpt-4o',
  callbacks: [handler],
});

const response = await llm.invoke('Hello, world!');`}</Code>
      </Section>
    </>
  );
}

function SecurityDocs() {
  return (
    <>
      <Section title="Tenant Isolation">
        <P>
          Every API request is scoped to your organization. Data is isolated at the
          database level — queries always include an org_id filter. No data is shared
          between tenants.
        </P>
      </Section>

      <Section title="Encryption">
        <P>
          All data is encrypted in transit (TLS 1.3) and at rest (AES-256).
          Sensitive fields (API keys, webhook secrets) are encrypted using AES-256-GCM
          with org-specific keys. Customer-managed encryption keys (BYOK) are supported
          for enterprise plans.
        </P>
      </Section>

      <Section title="Audit Trail">
        <P>
          Every action is recorded in an immutable audit log with SHA-256 hash chain
          verification. Audit logs are retained for the configured retention period
          (default: 365 days for compliance). Chain integrity can be verified at any
          time through the API or dashboard.
        </P>
      </Section>

      <Section title="Authentication">
        <P>
          AgentGuard supports JWT-based authentication with token rotation, SAML 2.0
          and OIDC single sign-on, IP allowlisting, and account lockout after failed
          login attempts. All passwords are hashed using bcrypt with a minimum strength
          requirement of 12 characters.
        </P>
      </Section>

      <Section title="Compliance Frameworks">
        <P>
          Built-in compliance detection and reporting for SOX, PCI-DSS, FFIEC, NYDFS-500,
          DORA, and EU AI Act. Pre-built report templates generate regulatory-ready
          documentation from your audit trail and detection history.
        </P>
      </Section>

      <Section title="API Key Security">
        <P>
          API keys are hashed before storage — the full key value is only shown once
          during creation. Keys can be scoped to specific permissions and revoked at
          any time. Rate limiting is enforced per-org with configurable limits.
        </P>
      </Section>
    </>
  );
}
