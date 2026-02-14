import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Changelog',
  description: 'Product updates and release notes for AgentGuard.',
};

interface Release {
  version: string;
  date: string;
  title: string;
  changes: string[];
}

const RELEASES: Release[] = [
  {
    version: '0.5.0',
    date: 'February 2026',
    title: 'AI Model Registry & Developer Experience',
    changes: [
      'AI Model Registry for tracking model provenance, risk profiles, and supply chain dependencies',
      'Interactive API documentation with Quick Start, API Reference, SDK, and LangChain guides',
      'Post-registration onboarding wizard with proxy endpoint and API key setup',
      'Password reset flow with self-service recovery',
      'CSV export and date range filtering on the incidents page',
      'SIEM/SOAR integration settings page (Splunk, Elastic, QRadar, Sentinel)',
    ],
  },
  {
    version: '0.4.0',
    date: 'February 2026',
    title: 'SDK Integrations & Enterprise Settings',
    changes: [
      'Python and Node.js SDKs with typed responses, retry logic, and custom exceptions',
      'LangChain and LlamaIndex callback handlers for automatic event capture',
      'OpenTelemetry span exporter for distributed tracing',
      'Team management with invite, remove, and role-based access control',
      'SSO (SAML 2.0 / OIDC), IP allowlisting, and data residency configuration',
      'Data retention policies with hot/warm/cold archival tiers',
    ],
  },
  {
    version: '0.3.0',
    date: 'February 2026',
    title: 'Red Team Testing & Shadow AI Discovery',
    changes: [
      'Built-in adversarial testing framework for probing agent vulnerabilities',
      'Shadow AI discovery to detect unauthorized LLM usage across your organization',
      'Threat intelligence feeds specific to LLM attack patterns',
      'Human review queue for escalated interactions',
    ],
  },
  {
    version: '0.2.0',
    date: 'January 2026',
    title: 'Compliance Monitoring & Cost Analytics',
    changes: [
      'Continuous compliance monitoring for SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, and EU AI Act',
      'Cost anomaly detection for unusual token consumption patterns',
      'Agent behavior policies — define guardrails per agent, per model',
      'Conversation risk scoring across entire threads',
    ],
  },
  {
    version: '0.1.0',
    date: 'December 2025',
    title: 'Initial Release',
    changes: [
      'Real-time LLM proxy with sub-millisecond overhead',
      'Hallucination detection for factual inconsistencies',
      'PII leak prevention with automatic blocking',
      'Prompt injection defense — direct, indirect, and jailbreak detection',
      'Real-time dashboard with incident management',
      'Slack, PagerDuty, and webhook alert integrations',
    ],
  },
];

export default function ChangelogPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-center text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Changelog
        </h1>
        <p className="mt-4 text-center text-lg text-muted-foreground">
          What&apos;s new in AgentGuard.
        </p>

        <div className="mt-16 space-y-0">
          {RELEASES.map((release) => (
            <div
              key={release.version}
              className="relative border-l-2 border-border pb-12 pl-8 last:pb-0"
            >
              {/* Timeline dot */}
              <div className="absolute -left-[7px] top-0 h-3 w-3 rounded-full border-2 border-primary bg-background" />

              <div className="flex items-baseline gap-3">
                <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
                  v{release.version}
                </span>
                <span className="text-sm text-muted-foreground">
                  {release.date}
                </span>
              </div>

              <h2 className="mt-3 text-lg font-semibold text-foreground">
                {release.title}
              </h2>

              <ul className="mt-3 space-y-2">
                {release.changes.map((change) => (
                  <li
                    key={change}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-muted-foreground/30" />
                    {change}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
