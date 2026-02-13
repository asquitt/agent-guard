import {
  Radio,
  Brain,
  ShieldAlert,
  Siren,
  Scale,
  TrendingUp,
  FileCheck,
  MessageSquareWarning,
  Target,
  Ghost,
  Shield,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface Feature {
  icon: LucideIcon;
  title: string;
  description: string;
}

const FEATURES: Feature[] = [
  {
    icon: Radio,
    title: 'Real-Time LLM Proxy',
    description:
      'Route all LLM traffic through a single monitoring layer with sub-millisecond overhead.',
  },
  {
    icon: Brain,
    title: 'Hallucination Detection',
    description:
      'Catch factual inconsistencies and fabricated outputs before they reach production.',
  },
  {
    icon: ShieldAlert,
    title: 'PII Leak Prevention',
    description:
      'Automatically detect and block personal data exposure in AI responses.',
  },
  {
    icon: Siren,
    title: 'Prompt Injection Defense',
    description:
      'Identify direct, indirect, and jailbreak injection attempts in real time.',
  },
  {
    icon: Scale,
    title: 'Compliance Monitoring',
    description:
      'Continuous monitoring against SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, and EU AI Act.',
  },
  {
    icon: TrendingUp,
    title: 'Cost Anomaly Detection',
    description:
      'Flag unusual token consumption patterns and runaway agent spending.',
  },
  {
    icon: FileCheck,
    title: 'Agent Behavior Policies',
    description:
      'Define guardrails and enforcement policies per agent, per model, per use case.',
  },
  {
    icon: MessageSquareWarning,
    title: 'Conversation Risk Tracking',
    description:
      'Score and monitor entire conversation threads for escalating risk patterns.',
  },
  {
    icon: Target,
    title: 'Red Team Testing',
    description:
      'Built-in adversarial testing framework to probe your agents before attackers do.',
  },
  {
    icon: Ghost,
    title: 'Shadow AI Discovery',
    description:
      'Detect unauthorized AI usage across your organization automatically.',
  },
  {
    icon: Shield,
    title: 'Threat Intelligence',
    description:
      'Curated threat feeds specific to LLM and agent attack patterns.',
  },
  {
    icon: Users,
    title: 'Human Review Queue',
    description:
      'Route flagged interactions to human reviewers with full context and audit trail.',
  },
];

export default function FeaturesGrid() {
  return (
    <section id="features" className="px-6 py-24">
      <div className="mx-auto max-w-7xl">
        <div className="mb-16 text-center">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
            Complete AI Agent Security
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
            Everything you need to monitor, detect, and respond to AI agent
            threats in one platform.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group rounded-xl border border-border bg-card p-6 transition-all hover:border-primary/30 hover:shadow-[0_0_30px_-10px] hover:shadow-primary/10"
            >
              <f.icon className="mb-4 h-6 w-6 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">
                {f.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
