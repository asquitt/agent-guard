'use client';

import { useState } from 'react';

interface IntegrationStepProps {
  apiKey: string;
  endpointId: string;
  onNext: () => void;
}

type Lang = 'python' | 'node' | 'curl';

function getSnippet(lang: Lang, apiKey: string, endpointId: string): string {
  const baseUrl = 'https://your-domain.agentguard.dev/api/v1/proxy';

  if (lang === 'python') {
    return `import openai

client = openai.OpenAI(
    api_key="${apiKey}",
    base_url="${baseUrl}/v1",
    default_headers={"X-Endpoint-Id": "${endpointId}"},
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)`;
  }

  if (lang === 'node') {
    return `import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "${apiKey}",
  baseURL: "${baseUrl}/v1",
  defaultHeaders: { "X-Endpoint-Id": "${endpointId}" },
});

const response = await client.chat.completions.create({
  model: "gpt-4",
  messages: [{ role: "user", content: "Hello!" }],
});
console.log(response.choices[0].message.content);`;
  }

  return `curl ${baseUrl}/v1/chat/completions \\
  -H "Authorization: Bearer ${apiKey}" \\
  -H "X-Endpoint-Id: ${endpointId}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'`;
}

const TABS: { id: Lang; label: string }[] = [
  { id: 'python', label: 'Python' },
  { id: 'node', label: 'Node.js' },
  { id: 'curl', label: 'cURL' },
];

export default function IntegrationStep({ apiKey, endpointId, onNext }: IntegrationStepProps) {
  const [lang, setLang] = useState<Lang>('python');
  const [copied, setCopied] = useState(false);

  const snippet = getSnippet(lang, apiKey, endpointId);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      <p className="text-sm text-muted-foreground">
        Point your OpenAI or Anthropic SDK at AgentGuard&apos;s proxy URL. All traffic will be
        automatically scanned for PII, compliance violations, and anomalies.
      </p>

      {/* Language tabs */}
      <div className="mt-6 flex gap-1 rounded-lg bg-muted p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setLang(tab.id)}
            className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              lang === tab.id
                ? 'bg-card text-foreground shadow-sm shadow-black/10'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Code block */}
      <div className="relative mt-3 rounded-lg bg-zinc-900 p-4">
        <button
          onClick={handleCopy}
          className="absolute right-3 top-3 rounded-md bg-zinc-700 px-2.5 py-1 text-xs text-zinc-300 hover:bg-muted"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
        <pre className="overflow-x-auto text-xs leading-relaxed text-zinc-300">
          <code>{snippet}</code>
        </pre>
      </div>

      <button
        onClick={onNext}
        className="mt-6 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-white hover:bg-primary/80"
      >
        Continue to test
      </button>
    </div>
  );
}
