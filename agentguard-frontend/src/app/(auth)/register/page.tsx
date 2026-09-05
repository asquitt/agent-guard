import type { Metadata } from 'next';
import Link from 'next/link';
import { Archive } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Registration Unavailable',
  description:
    'AgentGuard registration is unavailable because the standalone product is mothballed and preserved for reference.',
  robots: { index: false, follow: false },
};

export default function RegisterPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/50 px-4 py-12">
      <section className="w-full max-w-lg rounded-xl border border-border bg-card p-8 text-center shadow-sm shadow-black/10 sm:p-10">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-border bg-muted">
          <Archive className="h-6 w-6 text-primary" aria-hidden="true" />
        </div>
        <p className="mt-6 text-sm font-medium uppercase tracking-wider text-primary">
          Archived standalone project
        </p>
        <h1 className="mt-3 text-3xl font-bold text-foreground">
          Registration unavailable
        </h1>
        <p className="mt-4 leading-relaxed text-muted-foreground">
          AgentGuard is mothballed as a standalone product. No account or
          workspace can be created from this preserved route.
        </p>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Customer acquisition, deployments, and provider/runtime use remain
          unauthorized unless the repository&apos;s reactivation gates are met
          through a new portfolio decision.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            href="/"
            className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            View archived project
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            Existing account sign in
          </Link>
        </div>
      </section>
    </main>
  );
}
