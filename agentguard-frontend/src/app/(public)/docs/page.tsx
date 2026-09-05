import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Archived Documentation Reference',
  description:
    'Non-operational AgentGuard architecture and product concepts preserved for reference only.',
  robots: { index: false, follow: false },
};

const REFERENCE_AREAS = [
  {
    title: 'Architecture vocabulary',
    description:
      'Historical source describes proxy, detector, incident, trace, and organization-scoped boundaries.',
  },
  {
    title: 'Verification principles',
    description:
      'Preserved material distinguishes source, test, runtime, deployment, and customer evidence.',
  },
  {
    title: 'Extraction candidates',
    description:
      'Individual patterns may be evaluated for an active product only through bounded work with a named consumer.',
  },
];

export default function DocsPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-5xl">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-medium uppercase tracking-wider text-primary">
            Archived reference
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Documentation is non-operational
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            AgentGuard is mothballed as a standalone product. Public integration
            instructions are withheld because registration, deployments,
            provider connections, runtime spend, and traffic routing are not authorized.
          </p>
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {REFERENCE_AREAS.map((area) => (
            <article key={area.title} className="rounded-xl border border-border bg-card p-6">
              <h2 className="text-base font-semibold text-foreground">{area.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {area.description}
              </p>
            </article>
          ))}
        </div>

        <div className="mx-auto mt-10 max-w-3xl rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-6">
          <h2 className="text-lg font-semibold text-foreground">Do not activate from this page</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Do not create credentials, connect a provider, start services, or
            send request data based on archived source or historical examples.
          </p>
        </div>

        <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
          <Link href="/about" className="rounded-lg border border-border px-5 py-2.5 text-center text-sm font-medium text-foreground hover:bg-muted">
            Read archive disposition
          </Link>
          <Link href="/security" className="rounded-lg border border-border px-5 py-2.5 text-center text-sm font-medium text-foreground hover:bg-muted">
            Review security reference
          </Link>
        </div>
      </div>
    </section>
  );
}
