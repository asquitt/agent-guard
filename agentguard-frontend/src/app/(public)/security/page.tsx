import type { Metadata } from 'next';
import { Eye, FileCheck, KeyRound, Lock, Server, ShieldCheck } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Archived Security Reference',
  description:
    'Archived AgentGuard security boundaries and assurance caveats; not current deployment or control evidence.',
  robots: { index: false, follow: false },
};

interface Practice {
  icon: LucideIcon;
  title: string;
  description: string;
}

const PRACTICES: Practice[] = [
  {
    icon: Lock,
    title: 'Data protection',
    description: 'Historical implementation intent does not prove encryption, key custody, backup, retention, or deletion in a current environment.',
  },
  {
    icon: KeyRound,
    title: 'Access boundaries',
    description: 'Organization-scoped code requires direct positive and cross-tenant verification before it can support an isolation claim.',
  },
  {
    icon: Server,
    title: 'Runtime identity',
    description: 'No hosted architecture, active deployment, configuration, patch level, recovery posture, or cleanup state is asserted here.',
  },
  {
    icon: Eye,
    title: 'Monitoring surfaces',
    description: 'Preserved proxy, detector, and incident surfaces are not a managed security service or proof of continuous monitoring.',
  },
  {
    icon: ShieldCheck,
    title: 'Security assessment',
    description: 'This archive does not represent a current penetration test, remediation state, certification, or vulnerability-free claim.',
  },
  {
    icon: FileCheck,
    title: 'Audit evidence',
    description: 'Historical audit and review records are inputs, not proof of completeness, integrity, retention, or a control outcome.',
  },
];

export default function SecurityPage() {
  return (
    <>
      <section className="px-6 py-24">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-medium uppercase tracking-wider text-primary">
            Archived reference
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Security evidence is not current
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            AgentGuard is mothballed as a standalone product. Preserved controls
            and tests do not establish a deployed security posture or authorize
            production, provider, or customer traffic.
          </p>
        </div>
      </section>

      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-12 text-center text-3xl font-bold text-foreground">
            Archived verification boundaries
          </h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {PRACTICES.map((practice) => (
              <article key={practice.title} className="rounded-xl border border-border bg-card p-6">
                <practice.icon className="mb-4 h-6 w-6 text-primary" aria-hidden="true" />
                <h3 className="text-sm font-semibold text-foreground">{practice.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {practice.description}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="assurance" className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-3xl font-bold text-foreground">Archived assurance caveats</h2>
          <p className="mt-4 leading-relaxed text-muted-foreground">
            AgentGuard does not claim SOC 2 certification, an audit completion,
            a hosting posture, or a third-party assessment through this archive.
          </p>
        </div>
      </section>

      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-3xl font-bold text-foreground">Responsible disclosure</h2>
          <p className="mt-4 leading-relaxed text-muted-foreground">
            Security maintenance for archived assets remains in scope. Do not
            include live credentials, unnecessary personal data, or another
            organization&apos;s information in a report.
          </p>
          <a
            href="https://github.com/asquitt/agent-guard/security/advisories/new"
            className="mt-6 inline-block rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-primary hover:bg-muted"
          >
            Report an archived-source vulnerability privately
          </a>
        </div>
      </section>
    </>
  );
}
