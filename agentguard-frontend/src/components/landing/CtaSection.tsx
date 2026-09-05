import Link from 'next/link';

export default function CtaSection() {
  return (
    <section className="px-6 py-24">
      <div className="relative mx-auto max-w-4xl overflow-hidden rounded-2xl border border-border bg-card p-12 text-center sm:p-16">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/2 top-1/2 h-[300px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/10 blur-[100px]" />
        </div>

        <div className="relative">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
            Preserved for Reference
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            Public pages describe archived source and historical product intent.
            They do not invite registration, purchasing, deployment, or provider traffic.
          </p>

          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/docs"
              className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Browse Archived Reference
            </Link>
            <Link
              href="/status"
              className="rounded-lg border border-border px-6 py-3 text-sm font-medium text-foreground transition-colors hover:bg-background"
            >
              View Generic Status Surface
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
