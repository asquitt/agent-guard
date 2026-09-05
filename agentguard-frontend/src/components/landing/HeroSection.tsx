import Link from 'next/link';
import { Archive } from 'lucide-react';

export default function HeroSection() {
  return (
    <section className="relative overflow-hidden px-6 pb-24 pt-36">
      <div className="pointer-events-none absolute inset-0">
        <div className="glow-pulse absolute left-1/2 top-0 h-[600px] w-[800px] -translate-x-1/2 rounded-full bg-primary/5 blur-[120px]" />
      </div>

      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'radial-gradient(circle, hsl(0 0% 98%) 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      />

      <div className="relative mx-auto max-w-4xl text-center">
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground">
          <Archive className="h-4 w-4 text-primary" aria-hidden="true" />
          Archived reference · standalone product mothballed
        </div>

        <h1 className="text-5xl font-bold tracking-tight text-foreground sm:text-6xl lg:text-7xl">
          AgentGuard Is Preserved,
          <br />
          <span className="text-primary">Not an Active Standalone Product</span>
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
          AgentGuard is mothballed as a standalone product. Its source and
          selected public material remain available for preservation and bounded
          asset extraction.
        </p>

        <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground/80">
          Customer acquisition, registration, deployments, and provider/runtime
          use are not authorized.
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/about"
            className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Read Archive Disposition
          </Link>
          <Link
            href="/docs"
            className="rounded-lg border border-border px-6 py-3 text-sm font-medium text-foreground transition-colors hover:bg-card"
          >
            Browse Archived Reference
          </Link>
        </div>
      </div>
    </section>
  );
}
