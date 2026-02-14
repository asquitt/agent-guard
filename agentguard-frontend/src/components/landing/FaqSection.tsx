'use client';

import { useState } from 'react';
import { clsx } from 'clsx';

const FAQS = [
  {
    q: 'How does AgentGuard integrate with my existing AI stack?',
    a: 'AgentGuard works as a transparent proxy. Change your base URL to point at AgentGuard and all LLM traffic flows through our detection pipeline. One line of code, zero SDK changes. Supports OpenAI, Anthropic, Google, Mistral, Cohere, and any OpenAI-compatible endpoint.',
  },
  {
    q: 'What latency does the proxy add?',
    a: 'Our synchronous detection pipeline adds less than 2ms of latency per request. Heavy-weight analysis (hallucination detection, compliance checks) runs asynchronously after the response is returned to your user, so it never blocks the request path.',
  },
  {
    q: 'Which compliance frameworks are supported?',
    a: 'AgentGuard includes pre-built rulesets for SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, and the EU AI Act. Each framework maps to specific detectors and severity thresholds. Custom rules can be configured per organization.',
  },
  {
    q: 'Can I self-host AgentGuard?',
    a: 'Yes. Enterprise plans include the option for on-premise deployment within your VPC. We support AWS, GCP, and Azure. Data never leaves your infrastructure in the self-hosted model.',
  },
  {
    q: 'How does pricing work?',
    a: 'Pricing is based on the number of LLM requests proxied per month. Starter ($499/mo) covers up to 100K requests, Pro ($1,999/mo) covers up to 1M, and Enterprise is custom-priced for higher volumes. All plans include unlimited users and full detection capabilities.',
  },
  {
    q: 'What happens when a threat is detected?',
    a: 'Detectors can run in monitor mode (log only), warn mode (flag the response), or block mode (reject the request). Alerts are dispatched in real-time via Slack, PagerDuty, email, webhooks, or your SIEM. Every incident includes a full audit trail for compliance review.',
  },
];

export default function FaqSection() {
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl">
        <h2 className="mb-12 text-center text-3xl font-bold text-foreground">
          Frequently Asked Questions
        </h2>

        <div className="divide-y divide-border rounded-xl border border-border bg-card">
          {FAQS.map((faq, i) => {
            const isOpen = openIdx === i;
            return (
              <div key={i}>
                <button
                  onClick={() => setOpenIdx(isOpen ? null : i)}
                  className="flex w-full items-center justify-between px-6 py-5 text-left"
                  aria-expanded={isOpen}
                >
                  <span className="text-sm font-medium text-foreground pr-4">
                    {faq.q}
                  </span>
                  <span
                    className={clsx(
                      'shrink-0 text-muted-foreground transition-transform duration-200',
                      isOpen && 'rotate-45',
                    )}
                  >
                    +
                  </span>
                </button>
                <div
                  className={clsx(
                    'overflow-hidden transition-all duration-200',
                    isOpen ? 'max-h-96 pb-5' : 'max-h-0',
                  )}
                >
                  <p className="px-6 text-sm leading-relaxed text-muted-foreground">
                    {faq.a}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
