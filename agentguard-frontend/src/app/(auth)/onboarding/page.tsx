'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Logo from '@/components/ui/Logo';
import { createProxyEndpoint, createApiKey } from '@/lib/api';

const STEPS = ['Welcome', 'Proxy Endpoint', 'API Key', 'Integration'] as const;

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI', url: 'https://api.openai.com/v1' },
  { value: 'anthropic', label: 'Anthropic', url: 'https://api.anthropic.com/v1' },
  { value: 'azure_openai', label: 'Azure OpenAI', url: '' },
  { value: 'google', label: 'Google Gemini', url: 'https://generativelanguage.googleapis.com/v1beta' },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 2 state
  const [endpointName, setEndpointName] = useState('production');
  const [provider, setProvider] = useState('openai');
  const [endpointId, setEndpointId] = useState('');

  // Step 3 state
  const [apiKeyValue, setApiKeyValue] = useState('');
  const [copied, setCopied] = useState('');

  const currentProvider = PROVIDERS.find((p) => p.value === provider);

  async function handleCreateEndpoint() {
    setError('');
    setLoading(true);
    try {
      const ep = await createProxyEndpoint({
        name: endpointName,
        provider,
        target_url: currentProvider?.url ?? '',
      });
      setEndpointId(ep.id);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create endpoint');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateApiKey() {
    setError('');
    setLoading(true);
    try {
      const result = await createApiKey({ name: 'onboarding-key', scopes: ['proxy'] });
      setApiKeyValue(result.key);
      setStep(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create API key');
    } finally {
      setLoading(false);
    }
  }

  function copyToClipboard(text: string, label: string) {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(''), 2000);
  }

  const pythonSnippet = `from agentguard import AgentGuardClient

client = AgentGuardClient(
    api_key="${apiKeyValue || 'ag_live_...'}",
    endpoint_id="${endpointId || '<endpoint-id>'}",
)

response = client.proxy({
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello, world!"}],
})
print(response.choices[0].message.content)`;

  const nodeSnippet = `import { AgentGuardClient } from '@agentguard/sdk';

const client = new AgentGuardClient({
  apiKey: '${apiKeyValue || 'ag_live_...'}',
  endpointId: '${endpointId || '<endpoint-id>'}',
});

const response = await client.proxy({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Hello, world!' }],
});
console.log(response.choices[0].message.content);`;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-lg">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {STEPS.map((label, i) => (
              <div key={label} className="flex items-center">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium ${
                    i <= step
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {i < step ? '\u2713' : i + 1}
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={`mx-2 h-0.5 w-12 sm:w-20 ${
                      i < step ? 'bg-primary' : 'bg-muted'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-between text-xs text-muted-foreground">
            {STEPS.map((label) => (
              <span key={label}>{label}</span>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-8">
          {error && (
            <div className="mb-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {/* Step 0: Welcome */}
          {step === 0 && (
            <div className="text-center">
              <Logo className="mx-auto mb-4 h-12 w-12" />
              <h1 className="text-2xl font-bold text-foreground">
                Welcome to AgentGuard
              </h1>
              <p className="mt-3 text-sm text-muted-foreground">
                Let&apos;s get your AI agents protected in under 2 minutes.
                We&apos;ll set up a proxy endpoint, generate an API key,
                and show you how to integrate.
              </p>
              <button
                onClick={() => setStep(1)}
                className="mt-8 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Get Started
              </button>
              <button
                onClick={() => router.push('/dashboard')}
                className="mt-3 text-sm text-muted-foreground hover:text-foreground"
              >
                Skip setup — go to dashboard
              </button>
            </div>
          )}

          {/* Step 1: Create Proxy Endpoint */}
          {step === 1 && (
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                Create a Proxy Endpoint
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Route your LLM traffic through AgentGuard for real-time monitoring.
              </p>

              <div className="mt-6 space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">
                    Endpoint Name
                  </label>
                  <input
                    value={endpointName}
                    onChange={(e) => setEndpointName(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="e.g. production, staging"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">
                    LLM Provider
                  </label>
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    {PROVIDERS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                onClick={handleCreateEndpoint}
                disabled={loading || !endpointName}
                className="mt-6 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Endpoint'}
              </button>
            </div>
          )}

          {/* Step 2: Generate API Key */}
          {step === 2 && (
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                Generate an API Key
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Your proxy endpoint is ready. Now create an API key to authenticate requests.
              </p>

              <div className="mt-4 rounded-lg bg-green-500/10 px-4 py-3 text-sm text-green-400">
                Endpoint &quot;{endpointName}&quot; created successfully.
              </div>

              <button
                onClick={handleCreateApiKey}
                disabled={loading}
                className="mt-6 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate API Key'}
              </button>
            </div>
          )}

          {/* Step 3: Integration Code */}
          {step === 3 && (
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                Integrate AgentGuard
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Copy your API key and use the code snippets below.
              </p>

              {/* API Key Display */}
              <div className="mt-4">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Your API Key (save this — it won&apos;t be shown again)
                </label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 rounded-lg bg-muted px-3 py-2 font-mono text-xs text-foreground">
                    {apiKeyValue}
                  </code>
                  <button
                    onClick={() => copyToClipboard(apiKeyValue, 'key')}
                    className="shrink-0 rounded-md bg-muted px-3 py-2 text-xs font-medium text-foreground hover:bg-muted/80"
                  >
                    {copied === 'key' ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              </div>

              {/* Code Snippets */}
              <div className="mt-6 space-y-4">
                <CodeBlock
                  label="Python"
                  code={pythonSnippet}
                  onCopy={() => copyToClipboard(pythonSnippet, 'python')}
                  copied={copied === 'python'}
                />
                <CodeBlock
                  label="Node.js"
                  code={nodeSnippet}
                  onCopy={() => copyToClipboard(nodeSnippet, 'node')}
                  copied={copied === 'node'}
                />
              </div>

              <button
                onClick={() => router.push('/dashboard')}
                className="mt-6 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Go to Dashboard
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CodeBlock({
  label,
  code,
  onCopy,
  copied,
}: {
  label: string;
  code: string;
  onCopy: () => void;
  copied: boolean;
}) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <button
          onClick={onCopy}
          className="text-xs font-medium text-primary hover:text-primary/80"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-muted p-3 font-mono text-xs text-foreground">
        {code}
      </pre>
    </div>
  );
}
