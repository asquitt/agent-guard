import type { Metadata } from 'next';
import { Newspaper } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Blog - AgentGuard',
  description:
    'Insights on AI agent security, compliance, and incident response for financial services.',
};

export default function BlogPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-border bg-card">
          <Newspaper className="h-7 w-7 text-primary" />
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-foreground">
          Blog
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Coming soon.
        </p>
        <p className="mt-2 text-sm text-muted-foreground/60">
          We&apos;re working on sharing insights about AI agent security,
          compliance best practices, and the latest in threat detection.
        </p>
      </div>
    </section>
  );
}
