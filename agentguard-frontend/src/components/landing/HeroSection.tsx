import Link from 'next/link';
import { Shield } from 'lucide-react';

export default function HeroSection() {
  return (
    <section className="relative overflow-hidden px-6 pb-24 pt-36">
      {/* Background glow */}
      <div className="pointer-events-none absolute inset-0">
        <div className="glow-pulse absolute left-1/2 top-0 h-[600px] w-[800px] -translate-x-1/2 rounded-full bg-primary/5 blur-[120px]" />
      </div>

      {/* Dot grid pattern */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'radial-gradient(circle, hsl(0 0% 98%) 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      />

      <div className="relative mx-auto max-w-4xl text-center">
        {/* Badge */}
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground">
          <Shield className="h-4 w-4 text-primary" />
          AI Security for Financial Services
        </div>

        {/* Headline */}
        <h1 className="text-5xl font-bold tracking-tight text-foreground sm:text-6xl lg:text-7xl">
          Secure Every AI Agent
          <br />
          <span className="text-primary">Before It Becomes an Incident</span>
        </h1>

        {/* Subtitle */}
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
          Real-time monitoring, threat detection, and automated incident response
          for AI agents operating in regulated financial environments.
        </p>

        {/* CTAs */}
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link
            href="/register"
            className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Get Started Free
          </Link>
          <a
            href="#how-it-works"
            className="rounded-lg border border-border px-6 py-3 text-sm font-medium text-foreground transition-colors hover:bg-card"
          >
            See How It Works
          </a>
        </div>
      </div>
    </section>
  );
}
