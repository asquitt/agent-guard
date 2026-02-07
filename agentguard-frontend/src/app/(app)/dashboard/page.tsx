'use client';

import { useAuth } from '@/hooks/useAuth';

export default function DashboardPage() {
  const { user, organization } = useAuth();

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500">
          Welcome back, {user?.name ?? 'User'}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Total Requests" value="—" />
        <MetricCard label="Active Incidents" value="—" />
        <MetricCard label="Detection Rate" value="—" />
        <MetricCard label="Avg Latency" value="—" />
      </div>

      <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Getting Started
        </h2>
        <div className="space-y-3 text-sm text-gray-600">
          <p>
            <span className="font-medium text-gray-900">1.</span> Create a proxy
            endpoint to route your LLM traffic through AgentGuard
          </p>
          <p>
            <span className="font-medium text-gray-900">2.</span> Configure
            detectors for hallucination, PII, compliance, cost, and loop detection
          </p>
          <p>
            <span className="font-medium text-gray-900">3.</span> Set up alert
            destinations (Slack, PagerDuty, email) for real-time notifications
          </p>
          <p>
            <span className="font-medium text-gray-900">4.</span> Generate an API
            key and point your LLM SDK to{' '}
            <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
              {typeof window !== 'undefined' ? window.location.origin : ''}/api/v1/proxy
            </code>
          </p>
        </div>
      </div>

      <div className="mt-4 text-xs text-gray-400">
        Organization: {organization?.name} ({organization?.planTier} plan)
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}
