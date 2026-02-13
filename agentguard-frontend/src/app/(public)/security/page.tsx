import type { Metadata } from 'next';
import {
  Lock,
  KeyRound,
  Server,
  Eye,
  ShieldCheck,
  FileCheck,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Security - AgentGuard',
  description:
    'How AgentGuard protects your data with encryption, tenant isolation, and industry-standard security practices.',
};

interface Practice {
  icon: LucideIcon;
  title: string;
  description: string;
}

const PRACTICES: Practice[] = [
  {
    icon: Lock,
    title: 'Encryption',
    description:
      'All data is encrypted at rest using AES-256 and in transit using TLS 1.3. Encryption keys are managed through a dedicated KMS with automatic rotation.',
  },
  {
    icon: KeyRound,
    title: 'Access Control',
    description:
      'Role-based access control (RBAC) with strict tenant isolation. Every API request is authenticated and authorized. SSO and SAML supported for enterprise.',
  },
  {
    icon: Server,
    title: 'Infrastructure',
    description:
      'Hosted on SOC 2-compliant cloud infrastructure with network segmentation, private subnets, and WAF protection. All systems are regularly patched and hardened.',
  },
  {
    icon: Eye,
    title: 'Monitoring',
    description:
      '24/7 security monitoring with automated alerting. Intrusion detection, anomaly detection, and real-time log analysis across all infrastructure components.',
  },
  {
    icon: ShieldCheck,
    title: 'Penetration Testing',
    description:
      'Regular penetration testing by independent third-party firms. Vulnerability scanning and remediation with defined SLAs for critical findings.',
  },
  {
    icon: FileCheck,
    title: 'Audit Logging',
    description:
      'Immutable audit trails for all platform actions. Hash-chain verification ensures log integrity. Exportable for regulatory compliance reviews.',
  },
];

export default function SecurityPage() {
  return (
    <>
      {/* Hero */}
      <section className="px-6 py-24">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Security at AgentGuard
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            We secure AI agents for financial institutions — so security
            isn&apos;t just a feature, it&apos;s our foundation. Every layer
            of our platform is built with defense in depth.
          </p>
        </div>
      </section>

      {/* Practices grid */}
      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-12 text-center text-3xl font-bold text-foreground">
            Security Practices
          </h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {PRACTICES.map((p) => (
              <div
                key={p.title}
                className="rounded-xl border border-border bg-card p-6"
              >
                <p.icon className="mb-4 h-6 w-6 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">
                  {p.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {p.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SOC 2 */}
      <section id="soc2" className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-3xl font-bold text-foreground">
            SOC 2 Compliance
          </h2>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            AgentGuard is pursuing SOC 2 Type II certification. Our controls
            framework covers security, availability, processing integrity,
            confidentiality, and privacy — the five trust service criteria.
          </p>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            We maintain continuous compliance monitoring of our own
            infrastructure using the same rigor we apply to our
            customers&apos; AI agents. Our audit is currently in progress
            with a leading independent firm.
          </p>
          <p className="mt-4 text-sm text-muted-foreground/60">
            Enterprise customers can request our SOC 2 readiness report and
            security questionnaire responses under NDA.
          </p>
        </div>
      </section>

      {/* Responsible disclosure */}
      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-3xl font-bold text-foreground">
            Responsible Disclosure
          </h2>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            We take security vulnerabilities seriously. If you discover a
            security issue in our platform, please report it responsibly.
          </p>
          <div className="mt-6 rounded-xl border border-border bg-card p-6">
            <p className="text-sm text-muted-foreground">
              Report vulnerabilities to{' '}
              <a
                href="mailto:security@agentguard.dev"
                className="font-medium text-primary hover:text-primary/80"
              >
                security@agentguard.dev
              </a>
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              We will acknowledge receipt within 24 hours and provide a
              detailed response within 72 hours. We ask that you give us
              reasonable time to address the issue before public disclosure.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
