const PROVIDERS = [
  { name: 'OpenAI', desc: 'GPT-4o, o1, o3' },
  { name: 'Anthropic', desc: 'Claude 3.5, Claude 4' },
  { name: 'Google', desc: 'Gemini 2.0, PaLM' },
  { name: 'Meta', desc: 'Llama 3, Code Llama' },
  { name: 'Mistral', desc: 'Mistral Large, Codestral' },
  { name: 'Cohere', desc: 'Command R+' },
];

const TOOLS = [
  'Slack',
  'PagerDuty',
  'Splunk',
  'Datadog',
  'Jira',
  'Microsoft Teams',
  'Webhook',
  'Email',
];

export default function IntegrationsSection() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-5xl">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold text-foreground">
            Works With Every LLM Provider
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            One proxy endpoint. Every model. Full visibility across your entire
            AI stack, regardless of provider.
          </p>
        </div>

        {/* LLM Providers */}
        <div className="mb-12 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {PROVIDERS.map((p) => (
            <div
              key={p.name}
              className="flex flex-col items-center rounded-xl border border-border bg-card p-5 text-center transition-colors hover:border-primary/30"
            >
              <span className="text-lg font-semibold text-foreground">
                {p.name}
              </span>
              <span className="mt-1 text-xs text-muted-foreground">
                {p.desc}
              </span>
            </div>
          ))}
        </div>

        {/* Alert / SIEM Integrations */}
        <div className="text-center">
          <p className="mb-4 text-sm font-medium uppercase tracking-wider text-muted-foreground/60">
            Alert &amp; SIEM Integrations
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {TOOLS.map((tool) => (
              <span
                key={tool}
                className="rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground"
              >
                {tool}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
