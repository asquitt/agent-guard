import { Cable, ScanSearch, Zap } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface Step {
  icon: LucideIcon;
  title: string;
  description: string;
}

const STEPS: Step[] = [
  {
    icon: Cable,
    title: 'Connect',
    description:
      'Route your LLM API traffic through the AgentGuard proxy. One line of code to integrate with any provider.',
  },
  {
    icon: ScanSearch,
    title: 'Detect',
    description:
      'Real-time analysis across six detection categories: hallucinations, PII leaks, prompt injections, compliance violations, cost anomalies, and agent loops.',
  },
  {
    icon: Zap,
    title: 'Respond',
    description:
      'Automated incident response with configurable alerts, webhook integrations, and a human review queue for escalated cases.',
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-y border-border bg-card/30 px-6 py-24">
      <div className="mx-auto max-w-5xl">
        <div className="mb-16 text-center">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
            How It Works
          </h2>
          <p className="mt-4 text-muted-foreground">
            Deploy in minutes. Start detecting immediately.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-12 md:grid-cols-3 md:gap-8">
          {STEPS.map((step, i) => (
            <div key={step.title} className="step-connector relative text-center">
              <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-primary/30 bg-primary/10">
                <step.icon className="h-6 w-6 text-primary" />
              </div>
              <div className="mx-auto mb-2 flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                {i + 1}
              </div>
              <h3 className="text-lg font-semibold text-foreground">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
