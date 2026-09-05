import type { Metadata } from 'next';
import { Archive } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Archived Blog Reference',
  description:
    'The archived AgentGuard site does not publish an active standalone-product blog.',
  robots: { index: false, follow: false },
};

export default function BlogPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-border bg-card">
          <Archive className="h-7 w-7 text-primary" aria-hidden="true" />
        </div>
        <p className="text-sm font-medium uppercase tracking-wider text-primary">
          Archived reference
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight text-foreground">
          Blog publication is inactive
        </h1>
        <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
          AgentGuard is mothballed as a standalone product. This route is kept
          only so historical links resolve to an explicit archive boundary.
        </p>
      </div>
    </section>
  );
}
