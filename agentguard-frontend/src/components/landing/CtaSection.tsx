import Link from 'next/link';

export default function CtaSection() {
  return (
    <section className="px-6 py-24">
      <div className="relative mx-auto max-w-4xl overflow-hidden rounded-2xl border border-border bg-card p-12 text-center sm:p-16">
        {/* Background glow */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/2 top-1/2 h-[300px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/10 blur-[100px]" />
        </div>

        <div className="relative">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
            Start Securing Your AI Agents Today
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            Deploy in minutes. Detect threats in real time. Stay compliant
            without the overhead.
          </p>

          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              href="/register"
              className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Get Started Free
            </Link>
            <a
              href="mailto:sales@agentguard.dev"
              className="rounded-lg border border-border px-6 py-3 text-sm font-medium text-foreground transition-colors hover:bg-background"
            >
              Contact Sales
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
