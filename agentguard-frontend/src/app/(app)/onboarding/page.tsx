import Link from 'next/link';

export default function OnboardingPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/50 px-6 py-16">
      <section className="w-full max-w-2xl rounded-xl border border-border bg-card p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-primary">
          Archived workflow
        </p>
        <h1 className="mt-3 text-3xl font-bold text-foreground">
          Onboarding is unavailable
        </h1>
        <p className="mt-4 text-muted-foreground">
          AgentGuard is mothballed as a standalone product. This preserved build
          does not create proxy endpoints or API keys, send provider traffic, or
          claim that setup and detection were verified.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/dashboard"
            className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary/80"
          >
            Return to dashboard
          </Link>
          <Link
            href="/status"
            className="rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-foreground hover:bg-muted"
          >
            View archive status
          </Link>
        </div>
      </section>
    </main>
  );
}
