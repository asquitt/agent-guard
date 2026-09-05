import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Archived Terms Reference',
  description:
    'Archived AgentGuard terms caveats; no standalone service, registration, or commercial offer is available.',
  robots: { index: false, follow: false },
};

const SECTIONS = [
  {
    title: 'No standalone offer',
    body: 'AgentGuard is mothballed as a standalone product. This page does not offer registration, a workspace, a trial, a paid plan, a deployment, support, availability, or production use.',
  },
  {
    title: 'No service agreement',
    body: 'Archived source and public pages do not create a customer, pilot, subscription, license, data-processing, support, security, confidentiality, or service-level agreement.',
  },
  {
    title: 'Historical evidence is limited',
    body: 'Code, tests, fixtures, screenshots, status labels, and successful requests are historical evidence inputs. They do not prove current runtime, provider, enforcement, notification, compliance, security, or customer outcomes.',
  },
  {
    title: 'Reactivation is a separate decision',
    body: 'Any future standalone activity requires a new portfolio decision and every project-status gate. Applicable parties, scope, data roles, security duties, commercial terms, liability, termination, law, and verified notice channels would need new written terms.',
  },
];

export default function TermsPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-wider text-primary">
          Archived reference
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-foreground">
          Terms archive notice
        </h1>
        <p className="mt-4 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm leading-relaxed text-muted-foreground">
          This preserved page is not a terms-of-service document and does not
          authorize use of AgentGuard as a standalone service.
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
      </div>
    </section>
  );
}
