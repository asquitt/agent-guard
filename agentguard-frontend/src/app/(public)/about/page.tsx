import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Archived Project',
  description:
    'AgentGuard is a mothballed standalone project preserved for reference and bounded asset extraction.',
  robots: { index: false, follow: false },
};

const PRESERVED_AREAS = [
  {
    title: 'Product research',
    description:
      'Historical concepts for request visibility, detector evidence, incident review, and tenant boundaries remain available for study.',
  },
  {
    title: 'Source provenance',
    description:
      'Repository artifacts preserve prior implementation intent; their presence is not runtime, deployment, or customer proof.',
  },
  {
    title: 'Bounded extraction',
    description:
      'A reusable asset may move only through separately authorized work with a named active-product consumer.',
  },
];

export default function AboutPage() {
  return (
    <>
      <section className="px-6 py-24">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-medium uppercase tracking-wider text-primary">
            Archived reference
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            AgentGuard archive disposition
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            AgentGuard is mothballed as a standalone product. The repository is
            retained for preservation, security maintenance of archived assets,
            read-only evaluation, and bounded extraction with a named consumer.
          </p>
        </div>
      </section>

      <section className="border-t border-border px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-3xl font-bold text-foreground">
            What remains preserved
          </h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {PRESERVED_AREAS.map((area) => (
              <article key={area.title} className="rounded-xl border border-border bg-card p-6">
                <h3 className="text-base font-semibold text-foreground">{area.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  {area.description}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-border px-6 py-20 text-center">
        <h2 className="text-2xl font-bold text-foreground">Reference, not an offer</h2>
        <p className="mx-auto mt-4 max-w-2xl leading-relaxed text-muted-foreground">
          Archived pages do not authorize registration, purchasing, deployment,
          provider traffic, or production use.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link href="/docs" className="rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-foreground hover:bg-muted">
            Browse archived reference
          </Link>
          <Link href="/changelog" className="rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-foreground hover:bg-muted">
            View development history
          </Link>
        </div>
      </section>
    </>
  );
}
