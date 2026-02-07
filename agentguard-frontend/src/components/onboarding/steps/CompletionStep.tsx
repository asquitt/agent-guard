'use client';

import Link from 'next/link';

interface CompletionStepProps {
  incidentId: string | null;
  onFinish: () => void;
}

const LINKS = [
  { href: '/dashboard', label: 'View Dashboard', desc: 'See your security overview' },
  { href: '/dashboard/detectors', label: 'Configure Detectors', desc: 'Customize detection rules' },
  { href: '/dashboard/alerts', label: 'Set Up Alerts', desc: 'Get notified via Slack or email' },
];

export default function CompletionStep({ incidentId, onFinish }: CompletionStepProps) {
  const allLinks = incidentId
    ? [
        { href: `/dashboard/incidents/${incidentId}`, label: 'View Test Incident', desc: 'See the PII detection result' },
        ...LINKS,
      ]
    : LINKS;

  return (
    <div className="text-center">
      <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
        <span className="text-3xl">&#127881;</span>
      </div>
      <h2 className="text-xl font-semibold text-gray-900">You&apos;re all set!</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-gray-500">
        AgentGuard is now monitoring your LLM traffic. Explore the dashboard or configure
        detectors and alerts.
      </p>

      <div className="mx-auto mt-8 max-w-sm space-y-3">
        {allLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            onClick={onFinish}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 text-left transition-colors hover:border-primary-300 hover:bg-primary-50"
          >
            <div>
              <p className="text-sm font-medium text-gray-900">{link.label}</p>
              <p className="text-xs text-gray-500">{link.desc}</p>
            </div>
            <span className="text-gray-400">&rarr;</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
