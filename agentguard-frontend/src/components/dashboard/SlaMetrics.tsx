'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { getSlaMetrics } from '@/lib/api';

const PERIOD_OPTIONS = [
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
];

function latencyColor(ms: number | null): string {
  if (ms === null) return 'text-gray-400';
  if (ms < 100) return 'text-green-600';
  if (ms < 200) return 'text-yellow-600';
  return 'text-red-600';
}

function errorRateColor(rate: number): string {
  if (rate < 0.01) return 'text-green-600';
  if (rate < 0.05) return 'text-yellow-600';
  return 'text-red-600';
}

function uptimeColor(pct: number): string {
  if (pct >= 99.9) return 'text-green-600';
  if (pct >= 99) return 'text-yellow-600';
  return 'text-red-600';
}

function formatMs(ms: number | null): string {
  if (ms === null) return '—';
  return `${Math.round(ms)}ms`;
}

export function SlaMetricsSection() {
  const [days, setDays] = useState(30);

  const { data, isLoading } = useQuery({
    queryKey: ['sla-metrics', days],
    queryFn: () => getSlaMetrics(days),
  });

  return (
    <div className="mt-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Proxy SLA Metrics</h2>
        <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.days}
              onClick={() => setDays(opt.days)}
              className={clsx(
                'rounded-md px-3 py-1 text-sm font-medium transition-colors',
                days === opt.days
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SlaCard
          label="P95 Latency"
          value={isLoading ? '—' : formatMs(data?.p95LatencyMs ?? null)}
          colorClass={isLoading ? 'text-gray-400' : latencyColor(data?.p95LatencyMs ?? null)}
          subtitle={data ? `p50: ${formatMs(data.p50LatencyMs)} · p99: ${formatMs(data.p99LatencyMs)}` : undefined}
        />
        <SlaCard
          label="Error Rate"
          value={isLoading ? '—' : `${((data?.errorRate ?? 0) * 100).toFixed(2)}%`}
          colorClass={isLoading ? 'text-gray-400' : errorRateColor(data?.errorRate ?? 0)}
          subtitle={data ? `${data.totalRequests.toLocaleString()} total requests` : undefined}
        />
        <SlaCard
          label="Throughput"
          value={isLoading ? '—' : `${Math.round(data?.avgThroughputPerHour ?? 0)}/hr`}
          colorClass="text-gray-900"
          subtitle={`Last ${days} days`}
        />
        <SlaCard
          label="Uptime"
          value={isLoading ? '—' : `${(data?.uptimePct ?? 0).toFixed(2)}%`}
          colorClass={isLoading ? 'text-gray-400' : uptimeColor(data?.uptimePct ?? 0)}
          subtitle={data?.byProvider.length ? `${data.byProvider.length} provider(s)` : undefined}
        />
      </div>
    </div>
  );
}

function SlaCard({
  label,
  value,
  colorClass,
  subtitle,
}: {
  label: string;
  value: string;
  colorClass: string;
  subtitle?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={clsx('mt-1 text-2xl font-semibold', colorClass)}>{value}</p>
      {subtitle && <p className="mt-1 text-xs text-gray-400">{subtitle}</p>}
    </div>
  );
}
