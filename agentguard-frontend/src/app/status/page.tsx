'use client';

import { useEffect, useState } from 'react';
import { clsx } from 'clsx';

interface ComponentStatus {
  name: string;
  status: string;
  response_time_ms?: number;
  message?: string;
}

interface HealthData {
  status: string;
  components: ComponentStatus[];
}

const COMPONENT_LABELS: Record<string, string> = {
  database: 'Database (PostgreSQL)',
  redis: 'Cache (Redis)',
  celery: 'Background Workers',
};

const STATUS_CONFIG: Record<string, { label: string; color: string; dotColor: string }> = {
  ok: { label: 'Operational', color: 'text-green-700', dotColor: 'bg-green-500' },
  degraded: { label: 'Degraded', color: 'text-yellow-700', dotColor: 'bg-yellow-500' },
  error: { label: 'Outage', color: 'text-red-700', dotColor: 'bg-red-500' },
  unknown: { label: 'Unknown', color: 'text-gray-500', dotColor: 'bg-gray-400' },
};

const OVERALL_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  healthy: { label: 'All Systems Operational', bg: 'bg-green-50 border-green-200', text: 'text-green-800' },
  degraded: { label: 'Partial System Degradation', bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-800' },
  unhealthy: { label: 'System Outage Detected', bg: 'bg-red-50 border-red-200', text: 'text-red-800' },
};

export default function StatusPage() {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  async function fetchHealth() {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      const res = await fetch(`${apiUrl}/health/detailed`);
      const json = await res.json();
      setData(json);
      setLastChecked(new Date());
    } catch {
      setData({ status: 'unhealthy', components: [] });
      setLastChecked(new Date());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30_000);
    return () => clearInterval(interval);
  }, []);

  const overallConfig = OVERALL_CONFIG[data?.status ?? 'unhealthy'] ?? OVERALL_CONFIG.unhealthy;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-2xl px-4 py-12">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">AgentGuard Status</h1>
          <p className="mt-1 text-sm text-gray-500">Real-time platform health monitoring</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
          </div>
        ) : (
          <>
            {/* Overall status banner */}
            <div className={clsx('mb-8 rounded-xl border p-6 text-center', overallConfig.bg)}>
              <p className={clsx('text-lg font-semibold', overallConfig.text)}>
                {overallConfig.label}
              </p>
              {lastChecked && (
                <p className="mt-1 text-xs text-gray-500">
                  Last checked: {lastChecked.toLocaleTimeString()}
                </p>
              )}
            </div>

            {/* Components */}
            <div className="rounded-xl border border-gray-200 bg-white">
              <div className="border-b border-gray-100 px-6 py-4">
                <h2 className="text-sm font-semibold text-gray-900">Components</h2>
              </div>
              <div className="divide-y divide-gray-100">
                {/* API Server — always up if page loaded */}
                <ComponentRow
                  name="API Server"
                  status="ok"
                  responseTimeMs={undefined}
                  message={undefined}
                />
                {/* Proxy Gateway */}
                <ComponentRow
                  name="LLM Proxy Gateway"
                  status={data?.status === 'healthy' ? 'ok' : 'degraded'}
                  responseTimeMs={undefined}
                  message={undefined}
                />
                {(data?.components ?? []).map((c) => (
                  <ComponentRow
                    key={c.name}
                    name={COMPONENT_LABELS[c.name] ?? c.name}
                    status={c.status}
                    responseTimeMs={c.response_time_ms}
                    message={c.message}
                  />
                ))}
              </div>
            </div>

            {/* Refresh button */}
            <div className="mt-6 text-center">
              <button
                onClick={fetchHealth}
                className="text-sm text-primary-600 hover:text-primary-500"
              >
                Refresh now
              </button>
            </div>
          </>
        )}

        {/* Footer */}
        <div className="mt-12 text-center text-xs text-gray-400">
          <p>Checks run automatically every 30 seconds</p>
          <p className="mt-1">
            &copy; {new Date().getFullYear()} AgentGuard &mdash; AI Agent Security for Financial Services
          </p>
        </div>
      </div>
    </div>
  );
}

function ComponentRow({
  name,
  status,
  responseTimeMs,
  message,
}: {
  name: string;
  status: string;
  responseTimeMs: number | undefined;
  message: string | undefined;
}) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.unknown;

  return (
    <div className="flex items-center justify-between px-6 py-4">
      <div className="flex items-center gap-3">
        <div className={clsx('h-2.5 w-2.5 rounded-full', config.dotColor)} />
        <span className="text-sm font-medium text-gray-900">{name}</span>
        {message && <span className="text-xs text-gray-400">{message}</span>}
      </div>
      <div className="flex items-center gap-3">
        {responseTimeMs != null && (
          <span className="text-xs text-gray-400">{responseTimeMs}ms</span>
        )}
        <span className={clsx('text-sm font-medium', config.color)}>{config.label}</span>
      </div>
    </div>
  );
}
