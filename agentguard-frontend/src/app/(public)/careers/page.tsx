import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Archived Careers Reference',
  description:
    'AgentGuard is mothballed and does not advertise roles or accept applications through this archived site.',
  robots: { index: false, follow: false },
};

export default function CareersPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-sm font-medium uppercase tracking-wider text-primary">
          Archived reference
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          No standalone-product recruiting
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
          AgentGuard is mothballed as a standalone product. No roles,
          compensation, benefits, locations, or application channel are offered
          through this preserved route.
        </p>
        <div className="mx-auto mt-10 max-w-2xl rounded-xl border border-border bg-card p-6 text-left">
          <h2 className="text-lg font-semibold text-foreground">Application safety</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Do not send a resume, identity document, employment history, or
            other personal information in response to this archived material.
          </p>
        </div>
        <Link
          href="/about"
          className="mt-8 inline-block rounded-lg border border-border px-6 py-3 text-sm font-medium text-foreground hover:bg-muted"
        >
          Read archive disposition
        </Link>
      </div>
    </section>
  );
}
