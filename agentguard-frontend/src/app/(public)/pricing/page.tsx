import type { Metadata } from 'next';
import PricingSection from '@/components/landing/PricingSection';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Pricing - AgentGuard',
  description: 'Simple, transparent pricing for AI agent security. Start free, scale with confidence.',
};

const FAQ = [
  {
    q: 'What counts as an LLM request?',
    a: 'Every API call that passes through the AgentGuard proxy counts as one request. This includes both input and output — we measure requests, not tokens.',
  },
  {
    q: 'Can I change plans at any time?',
    a: 'Yes. Upgrade instantly and we prorate the difference. Downgrades take effect at the end of your billing cycle.',
  },
  {
    q: 'Do you offer annual billing?',
    a: 'Yes. Annual plans receive a 20% discount. Contact us for custom enterprise agreements.',
  },
  {
    q: 'What happens if I exceed my request limit?',
    a: 'We never block your traffic. Overages are billed at the per-request rate for your tier. We send alerts at 80% and 100% usage.',
  },
  {
    q: 'Is there a free trial?',
    a: 'Every account starts with a 14-day free trial of the Pro plan. No credit card required.',
  },
  {
    q: 'What compliance frameworks do you support?',
    a: 'SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, and EU AI Act. Enterprise plans include custom compliance reporting.',
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="pt-8">
        <PricingSection />
      </div>

      {/* Comparison table */}
      <section className="px-6 pb-16">
        <div className="mx-auto max-w-4xl">
          <h2 className="mb-8 text-center text-2xl font-bold text-foreground">
            Compare Plans
          </h2>
          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="px-6 py-4 font-medium text-muted-foreground">Feature</th>
                  <th className="px-6 py-4 font-medium text-muted-foreground">Starter</th>
                  <th className="px-6 py-4 font-medium text-primary">Pro</th>
                  <th className="px-6 py-4 font-medium text-muted-foreground">Enterprise</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                <CompareRow feature="LLM Requests" starter="100K/mo" pro="1M/mo" enterprise="Unlimited" />
                <CompareRow feature="Detection Categories" starter="3" pro="All 10+" enterprise="Custom" />
                <CompareRow feature="Data Retention" starter="7 days" pro="90 days" enterprise="Unlimited" />
                <CompareRow feature="Alert Channels" starter="Email" pro="Email, Slack, PagerDuty" enterprise="All + custom" />
                <CompareRow feature="Red Team Testing" starter="-" pro="Yes" enterprise="Yes" />
                <CompareRow feature="SSO / SAML" starter="-" pro="-" enterprise="Yes" />
                <CompareRow feature="Data Residency" starter="-" pro="-" enterprise="Yes" />
                <CompareRow feature="Model Registry" starter="View only" pro="Full CRUD" enterprise="Full CRUD" />
                <CompareRow feature="API Keys" starter="2" pro="10" enterprise="Unlimited" />
                <CompareRow feature="Team Members" starter="5" pro="25" enterprise="Unlimited" />
                <CompareRow feature="Support" starter="Community" pro="Priority" enterprise="Dedicated CSM" />
                <CompareRow feature="SLA" starter="-" pro="99.9%" enterprise="99.99%" />
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-6 pb-24">
        <div className="mx-auto max-w-3xl">
          <h2 className="mb-8 text-center text-2xl font-bold text-foreground">
            Frequently Asked Questions
          </h2>
          <div className="space-y-4">
            {FAQ.map((item) => (
              <div
                key={item.q}
                className="rounded-xl border border-border bg-card p-6"
              >
                <h3 className="text-sm font-semibold text-foreground">{item.q}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{item.a}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 text-center">
            <p className="text-sm text-muted-foreground">
              Still have questions?{' '}
              <Link href="/about" className="font-medium text-primary hover:text-primary/80">
                Contact our team
              </Link>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

function CompareRow({
  feature,
  starter,
  pro,
  enterprise,
}: {
  feature: string;
  starter: string;
  pro: string;
  enterprise: string;
}) {
  return (
    <tr>
      <td className="px-6 py-3 font-medium text-foreground">{feature}</td>
      <td className="px-6 py-3 text-muted-foreground">{starter}</td>
      <td className="px-6 py-3 font-medium text-foreground">{pro}</td>
      <td className="px-6 py-3 text-muted-foreground">{enterprise}</td>
    </tr>
  );
}
