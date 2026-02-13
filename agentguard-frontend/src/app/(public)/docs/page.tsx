import type { Metadata } from 'next';
import {
  Rocket,
  FileCode,
  Package,
  Terminal,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Documentation - AgentGuard',
  description:
    'Developer documentation for integrating AgentGuard into your AI agent infrastructure.',
};

interface DocCard {
  icon: LucideIcon;
  title: string;
  description: string;
  badge?: string;
}

const DOCS: DocCard[] = [
  {
    icon: Rocket,
    title: 'Quick Start Guide',
    description:
      'Get up and running with AgentGuard in under 5 minutes. Route your first LLM request through the proxy and see detections in real time.',
    badge: 'Start Here',
  },
  {
    icon: FileCode,
    title: 'API Reference',
    description:
      'Complete REST API documentation for incidents, agents, detectors, alerts, compliance, and analytics endpoints.',
  },
  {
    icon: Package,
    title: 'Node.js SDK',
    description:
      'Install the @agentguard/node package and integrate with Express, Next.js, or any Node application.',
  },
  {
    icon: Terminal,
    title: 'Python SDK',
    description:
      'Install agentguard-python and integrate with FastAPI, Django, or any Python application.',
  },
];

export default function DocsPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-5xl">
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Documentation
          </h1>
          <p className="mt-4 text-lg text-muted-foreground">
            Everything you need to integrate AgentGuard into your stack.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2">
          {DOCS.map((doc) => (
            <div
              key={doc.title}
              className="group relative rounded-xl border border-border bg-card p-6 transition-all hover:border-primary/30 hover:shadow-[0_0_30px_-10px] hover:shadow-primary/10"
            >
              {doc.badge && (
                <span className="mb-3 inline-block rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                  {doc.badge}
                </span>
              )}
              <doc.icon className="mb-4 h-6 w-6 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">
                {doc.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {doc.description}
              </p>
              <p className="mt-4 text-xs font-medium text-muted-foreground/50">
                Coming soon
              </p>
            </div>
          ))}
        </div>

        <div className="mt-16 text-center">
          <p className="text-sm text-muted-foreground">
            Need help now?{' '}
            <a
              href="mailto:support@agentguard.dev"
              className="font-medium text-primary hover:text-primary/80"
            >
              Contact our engineering team
            </a>
          </p>
        </div>
      </div>
    </section>
  );
}
