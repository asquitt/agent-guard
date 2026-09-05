import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Archived Development Reference',
  description:
    'Archived AgentGuard development context; repository history is not release, deployment, or customer proof.',
  robots: { index: false, follow: false },
};

const PRESERVATION_CAVEATS = [
  'Repository commits and tests do not prove a deployed service.',
  'Historical screenshots and fixtures do not prove customer use.',
  'Status responses do not prove provider, detector, or end-to-end behavior.',
  'No standalone release or reactivation is represented by this archive.',
];

export default function ChangelogPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl">
        <p className="text-center text-sm font-medium uppercase tracking-wider text-primary">
          Archived reference
        </p>
        <h1 className="mt-3 text-center text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Preserved development context
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-center text-lg leading-relaxed text-muted-foreground">
          AgentGuard is mothballed as a standalone product. This page is not a
          versioned release history and does not identify an active deployment.
        </p>

        <div className="mt-14 rounded-xl border border-border bg-card p-8">
          <h2 className="text-xl font-semibold text-foreground">
            Evidence boundaries
          </h2>
          <ul className="mt-6 space-y-3">
            {PRESERVATION_CAVEATS.map((item) => (
              <li key={item} className="flex items-start gap-3 text-sm text-muted-foreground">
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/docs" className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted">
            Browse archived reference
          </Link>
          <Link href="/security" className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted">
            Review security caveats
          </Link>
        </div>
      </div>
    </section>
  );
}
