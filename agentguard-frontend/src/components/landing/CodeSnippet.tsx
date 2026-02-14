'use client';

import { useState } from 'react';
import { clsx } from 'clsx';

const SNIPPETS = {
  python: `import openai

# Before — direct to provider
# client = openai.OpenAI()

# After — route through AgentGuard
client = openai.OpenAI(
    base_url="https://proxy.agentguard.dev/v1",
    api_key="ag_sk_...",  # Your AgentGuard API key
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "..."}],
)
# That's it. Full detection is automatic.`,
  node: `import OpenAI from "openai";

// Before — direct to provider
// const client = new OpenAI();

// After — route through AgentGuard
const client = new OpenAI({
  baseURL: "https://proxy.agentguard.dev/v1",
  apiKey: "ag_sk_...", // Your AgentGuard API key
});

const response = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "..." }],
});
// That's it. Full detection is automatic.`,
};

type Lang = keyof typeof SNIPPETS;

export default function CodeSnippet() {
  const [lang, setLang] = useState<Lang>('python');

  return (
    <section className="bg-card/50 px-6 py-24">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 text-center">
          <h2 className="text-3xl font-bold text-foreground">
            One Line of Code. Full Protection.
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Just change your base URL. No SDK, no wrapper, no agent
            modifications. Works with every OpenAI-compatible client.
          </p>
        </div>

        {/* Language tabs */}
        <div className="mb-4 flex gap-2">
          {(['python', 'node'] as Lang[]).map((l) => (
            <button
              key={l}
              onClick={() => setLang(l)}
              className={clsx(
                'rounded-lg px-4 py-1.5 text-sm font-medium transition-colors',
                l === lang
                  ? 'bg-primary text-white'
                  : 'bg-muted text-muted-foreground hover:text-foreground',
              )}
            >
              {l === 'python' ? 'Python' : 'Node.js'}
            </button>
          ))}
        </div>

        <div className="overflow-hidden rounded-xl border border-border bg-[#0d1117]">
          <div className="flex items-center gap-1.5 border-b border-border/30 px-4 py-2.5">
            <span className="h-3 w-3 rounded-full bg-red-500/60" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/60" />
            <span className="h-3 w-3 rounded-full bg-green-500/60" />
            <span className="ml-3 text-xs text-muted-foreground/50">
              {lang === 'python' ? 'app.py' : 'index.ts'}
            </span>
          </div>
          <pre className="overflow-x-auto p-6 text-sm leading-relaxed text-gray-300">
            <code>{SNIPPETS[lang]}</code>
          </pre>
        </div>
      </div>
    </section>
  );
}
