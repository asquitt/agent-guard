import { Check } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';

interface Tier {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  ctaHref: string;
  highlighted: boolean;
}

const TIERS: Tier[] = [
  {
    name: 'Starter',
    price: '$499',
    period: '/month',
    description: 'For teams getting started with AI agent security.',
    features: [
      'Up to 100K LLM requests/mo',
      '3 detection categories',
      'Email alerts',
      'Basic dashboard',
      '7-day data retention',
      'Community support',
    ],
    cta: 'Get Started',
    ctaHref: '/register',
    highlighted: false,
  },
  {
    name: 'Pro',
    price: '$1,999',
    period: '/month',
    description: 'Full detection coverage for scaling AI operations.',
    features: [
      'Up to 1M LLM requests/mo',
      'All 6 detection categories',
      'Slack + PagerDuty + Webhooks',
      'Full analytics dashboard',
      '90-day data retention',
      'Red team testing',
      'Agent behavior policies',
      'Priority support',
    ],
    cta: 'Get Started',
    ctaHref: '/register',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'Dedicated compliance and deployment for large orgs.',
    features: [
      'Unlimited LLM requests',
      'Custom detection rules',
      'SSO / SAML',
      'Data residency controls',
      'Unlimited retention',
      'Dedicated CSM',
      'SLA guarantees',
      'On-premise deployment',
    ],
    cta: 'Contact Sales',
    ctaHref: '#contact',
    highlighted: false,
  },
];

export default function PricingSection() {
  return (
    <section id="pricing" className="px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="mb-16 text-center">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
            Simple, Transparent Pricing
          </h2>
          <p className="mt-4 text-muted-foreground">
            Start free. Scale with confidence.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={clsx(
                'flex flex-col rounded-xl border p-8 transition-all',
                tier.highlighted
                  ? 'border-primary bg-card shadow-[0_0_60px_-15px] shadow-primary/20'
                  : 'border-border bg-card hover:border-primary/20',
              )}
            >
              {tier.highlighted && (
                <span className="mb-4 inline-block self-start rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                  Most Popular
                </span>
              )}

              <h3 className="text-lg font-semibold text-foreground">
                {tier.name}
              </h3>

              <div className="mt-4">
                <span className="text-4xl font-bold text-foreground">
                  {tier.price}
                </span>
                {tier.period && (
                  <span className="text-muted-foreground">{tier.period}</span>
                )}
              </div>

              <p className="mt-3 text-sm text-muted-foreground">
                {tier.description}
              </p>

              <Link
                href={tier.ctaHref}
                className={clsx(
                  'mt-6 block w-full rounded-lg py-2.5 text-center text-sm font-medium transition-colors',
                  tier.highlighted
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'border border-border text-foreground hover:bg-muted/50',
                )}
              >
                {tier.cta}
              </Link>

              <ul className="mt-6 flex-1 space-y-3">
                {tier.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
