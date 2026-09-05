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
  if (ms === null) return 'text-muted-foreground/60';
  if (ms < 100) return 'text-green-600';
  if (ms < 200) return 'text-yellow-600';
  return 'text-red-600';
}

function errorRateColor(rate: number): string {
  if (rate < 0.01) return 'text-green-600';
  if (rate < 0.05) return 'text-yellow-600';
  return 'text-red-600';
}

function successRateColor(pct: number): string {
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

  const { data, isLoading, isError } = useQuery({
    queryKey: ['sla-metrics', days],
    queryFn: () => getSlaMetrics(days),
  });
  const hasSamples = Boolean(data && data.totalRequests > 0);
  const metricsUnavailable = isLoading || isError || !data;

  return (
    <div className="mt-8">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Observed Proxy Metrics</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Calculated from recorded organization requests, not a service-level commitment.
          </p>
        </div>
        <div className="flex gap-1 rounded-lg bg-muted p-1">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.days}
              type="button"
              aria-pressed={days === opt.days}
              onClick={() => setDays(opt.days)}
              className={clsx(
                'rounded-md px-3 py-1 text-sm font-medium transition-colors',
                days === opt.days
                  ? 'bg-card text-foreground shadow-sm shadow-black/10'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isError && (
        <p role="alert" className="mb-4 text-sm text-muted-foreground">
          Observed metrics are unavailable.
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SlaCard
          label="P95 Latency"
          value={isLoading ? '—' : formatMs(data?.p95LatencyMs ?? null)}
          colorClass={isLoading ? 'text-muted-foreground/60' : latencyColor(data?.p95LatencyMs ?? null)}
          subtitle={data ? `p50: ${formatMs(data.p50LatencyMs)} · p99: ${formatMs(data.p99LatencyMs)}` : undefined}
        />
        <SlaCard
          label="Error Rate"
          value={hasSamples && data ? `${(data.errorRate * 100).toFixed(2)}%` : '—'}
          colorClass={hasSamples && data ? errorRateColor(data.errorRate) : 'text-muted-foreground/60'}
          subtitle={data ? `${data.totalRequests.toLocaleString()} total requests` : undefined}
        />
        <SlaCard
          label="Throughput"
          value={hasSamples && data ? `${Math.round(data.avgThroughputPerHour)}/hr` : '—'}
          colorClass={hasSamples ? 'text-foreground' : 'text-muted-foreground/60'}
          subtitle={
            metricsUnavailable
              ? 'Metric unavailable'
              : hasSamples
                ? `Last ${days} days`
                : 'No recorded requests in this period'
          }
        />
        <SlaCard
          label="Successful response ratio"
          value={
            !hasSamples || !data
              ? '—'
              : `${data.uptimePct.toFixed(2)}%`
          }
          colorClass={
            !hasSamples || !data
              ? 'text-muted-foreground/60'
              : successRateColor(data.uptimePct)
          }
          subtitle={
            data
              ? data.totalRequests === 0
                ? 'No recorded requests in this period'
                : `Based on ${data.totalRequests.toLocaleString()} recorded requests`
              : undefined
          }
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
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={clsx('mt-1 text-2xl font-semibold', colorClass)}>{value}</p>
      {subtitle && <p className="mt-1 text-xs text-muted-foreground/60">{subtitle}</p>}
    </div>
  );
}
