import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Archived Data-Handling Reference',
  description:
    'Archived AgentGuard data-handling caveats; this page is not an active service privacy notice.',
  robots: { index: false, follow: false },
};

const SECTIONS = [
  {
    title: 'No active collection offer',
    body: 'This archived site does not invite account creation, workspace enrollment, provider traffic, or submission of customer, regulated, confidential, or sensitive data.',
  },
  {
    title: 'Historical data surfaces',
    body: 'Preserved source contains account, organization, request, response, detector, incident, audit, and operational concepts. Their presence does not identify a live data controller, processor, deployment, retention policy, or subprocessor chain.',
  },
  {
    title: 'Do not infer controls',
    body: 'Source code, settings, tests, status labels, and screenshots do not prove encryption, redaction, tenant isolation, retention, deletion, backup, residency, or incident-response behavior in any environment.',
  },
  {
    title: 'Reactivation requires a new notice',
    body: 'Any future authorized service would need a responsible legal entity, verified contact channel, data inventory, purposes, roles, locations, retention, deletion, security terms, and applicable rights before accepting data.',
  },
];

export default function PrivacyPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-wider text-primary">
          Archived reference
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-foreground">
          Data-handling archive notice
        </h1>
        <p className="mt-4 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm leading-relaxed text-muted-foreground">
          AgentGuard is mothballed as a standalone product. This preserved page
          is not an active privacy policy or data-processing agreement.
        </p>

        <div className="mt-12 space-y-10">
          {SECTIONS.map((section) => (
            <article key={section.title}>
              <h2 className="text-lg font-semibold text-foreground">{section.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {section.body}
              </p>
            </article>
          ))}
        </div>

        <Link href="/security" className="mt-10 inline-block text-sm font-medium text-primary hover:text-primary/80">
          Review archived security caveats
        </Link>
      </div>
    </section>
  );
}
