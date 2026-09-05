import type { Metadata } from 'next';
import Link from 'next/link';

import ArchiveDispositionSection from '@/components/landing/PricingSection';

export const metadata: Metadata = {
  title: 'Archived Pricing Reference',
  description:
    'AgentGuard offers no standalone prices, plans, trials, pilots, or workspaces while the project is mothballed.',
  robots: { index: false, follow: false },
};

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      <ArchiveDispositionSection />
      <section className="px-6 pb-24">
        <div className="mx-auto max-w-3xl rounded-xl border border-border bg-card p-8 text-center">
          <p className="text-sm font-medium uppercase tracking-wider text-primary">
            Archived pricing route
          </p>
          <h1 className="mt-3 text-2xl font-bold text-foreground">
            No standalone offering is available
          </h1>
          <p className="mt-4 leading-relaxed text-muted-foreground">
            This preserved URL does not publish commercial terms or invite a
            purchase. Reactivation would require a new portfolio decision and
            every gate in the repository&apos;s project-status authority.
          </p>
          <Link
            href="/about"
            className="mt-7 inline-block rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-foreground hover:bg-muted"
          >
            Read archive disposition
          </Link>
        </div>
      </section>
    </div>
  );
}
