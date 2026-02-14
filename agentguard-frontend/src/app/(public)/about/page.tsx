import type { Metadata } from 'next';
import { Shield, Scale, Code } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'About',
  description:
    'AgentGuard secures AI agents in regulated financial environments with real-time detection, compliance monitoring, and automated incident response.',
  openGraph: {
    title: 'About AgentGuard',
    description:
      'AgentGuard secures AI agents in regulated financial environments with real-time detection, compliance monitoring, and automated incident response.',
  },
};

interface Value {
  icon: LucideIcon;
  title: string;
  description: string;
}

const VALUES: Value[] = [
  {
    icon: Shield,
    title: 'Security First',
    description:
      'Every design decision starts with security. We build defense-in-depth protections so your AI agents operate safely in production.',
  },
  {
    icon: Scale,
    title: 'Compliance Native',
    description:
      'Regulatory compliance is built into the platform, not bolted on. SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, and EU AI Act — covered from day one.',
  },
  {
    icon: Code,
    title: 'Developer Friendly',
    description:
      'One line of code to integrate. Full API access, SDKs for Node and Python, and a real-time dashboard your security team will actually use.',
  },
];

export default function AboutPage() {
  return (
    <>
      {/* Hero */}
      <section className="px-6 py-24">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Securing the Future of AI
            <br />
            <span className="text-primary">in Financial Services</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Financial institutions are deploying AI agents at scale — for
            customer service, trading, advisory, and operations. AgentGuard
            ensures these agents operate securely, compliantly, and
            transparently.
          </p>
        </div>
      </section>

      {/* Mission */}
      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-2xl font-bold text-foreground">Our Mission</h2>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            AI agents are transforming financial services, but they introduce
            novel risks — hallucinations that mislead customers, prompt
            injections that exfiltrate data, and compliance violations that
            trigger regulatory action. We built AgentGuard because securing AI
            agents shouldn&apos;t require building an entire security
            infrastructure from scratch.
          </p>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            Our platform gives security teams a single pane of glass to monitor
            every AI agent interaction, detect threats in real time, and respond
            automatically — with full audit trails for regulators.
          </p>
        </div>
      </section>

      {/* Values */}
      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-12 text-center text-3xl font-bold text-foreground">
            What We Believe
          </h2>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {VALUES.map((v) => (
              <div
                key={v.title}
                className="rounded-xl border border-border bg-card p-6"
              >
                <v.icon className="mb-4 h-6 w-6 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">
                  {v.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {v.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-foreground">Our Team</h2>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            We&apos;re a team of security engineers, AI researchers, and
            financial services veterans building the security infrastructure
            that the AI agent era demands.
          </p>
          <Link
            href="/careers"
            className="mt-8 inline-block rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Join Us
          </Link>
        </div>
      </section>
    </>
  );
}
