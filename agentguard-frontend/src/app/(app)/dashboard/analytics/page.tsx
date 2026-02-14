'use client';

import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { getTimeSeries, getProviderComparison } from '@/lib/api';
import type { TimeSeriesBucket, ProviderPerformance } from '@/lib/api';
import { AnalyticsSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { BarChart3, Download } from 'lucide-react';

const TIME_RANGES = [
  { label: '1h', days: 0.04, granularity: 'hourly' },
  { label: '24h', days: 1, granularity: 'hourly' },
  { label: '7d', days: 7, granularity: 'auto' },
  { label: '30d', days: 30, granularity: 'daily' },
  { label: '90d', days: 90, granularity: 'daily' },
] as const;

type MetricKey = 'requests' | 'incidents' | 'avgLatencyMs' | 'totalCostUsd' | 'totalTokens' | 'detections' | 'errorCount';

const METRIC_OPTIONS: { key: MetricKey; label: string; format: (v: number | null) => string }[] = [
  { key: 'requests', label: 'Requests', format: (v) => String(v ?? 0) },
  { key: 'incidents', label: 'Incidents', format: (v) => String(v ?? 0) },
  { key: 'detections', label: 'Detections', format: (v) => String(v ?? 0) },
  { key: 'avgLatencyMs', label: 'Avg Latency (ms)', format: (v) => v != null ? `${v.toFixed(0)}ms` : '-' },
  { key: 'totalCostUsd', label: 'Cost (USD)', format: (v) => `$${(v ?? 0).toFixed(2)}` },
  { key: 'totalTokens', label: 'Tokens', format: (v) => (v ?? 0).toLocaleString() },
  { key: 'errorCount', label: 'Errors', format: (v) => String(v ?? 0) },
];

export default function AnalyticsPage() {
  const [rangeIdx, setRangeIdx] = useState(2); // 7d default
  const [activeMetric, setActiveMetric] = useState<MetricKey>('requests');

  const range = TIME_RANGES[rangeIdx];

  const { data: tsData, isLoading } = useQuery({
    queryKey: ['time-series', range.days, range.granularity],
    queryFn: () => getTimeSeries(Math.max(1, Math.ceil(range.days)), range.granularity),
  });

  const { data: providerData } = useQuery({
    queryKey: ['provider-comparison', Math.max(1, Math.ceil(range.days))],
    queryFn: () => getProviderComparison(Math.max(1, Math.ceil(range.days))),
  });

  const buckets = tsData?.buckets ?? [];
  const providers = providerData?.providers ?? [];
  const metricConfig = METRIC_OPTIONS.find((m) => m.key === activeMetric)!;

  const exportCsv = useCallback(() => {
    if (!buckets.length) return;
    const headers = ['Timestamp', ...METRIC_OPTIONS.map((m) => m.label)];
    const rows = buckets.map((b) => [
      b.bucket,
      ...METRIC_OPTIONS.map((m) => {
        const v = b[m.key];
        return typeof v === 'number' ? v : 0;
      }),
    ]);
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agentguard-analytics-${range.label}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [buckets, range.label]);

  // Compute summary stats
  const summary = useMemo(() => {
    if (!buckets.length) return { total: 0, avg: 0, max: 0, maxBucket: '' };
    const values = buckets.map((b) => {
      const v = b[activeMetric];
      return typeof v === 'number' ? v : 0;
    });
    const total = values.reduce((a, b) => a + b, 0);
    const max = Math.max(...values);
    const maxIdx = values.indexOf(max);
    return {
      total,
      avg: total / values.length,
      max,
      maxBucket: buckets[maxIdx]?.bucket ?? '',
    };
  }, [buckets, activeMetric]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Analytics</h1>
        <p className="text-sm text-muted-foreground">Time-series metrics across all your LLM traffic</p>
      </div>

      {/* Time range selector */}
      <div className="mb-6 flex items-center gap-2">
        {TIME_RANGES.map((r, i) => (
          <button
            key={r.label}
            onClick={() => setRangeIdx(i)}
            className={clsx(
              'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              i === rangeIdx
                ? 'bg-primary text-white'
                : 'bg-muted text-muted-foreground hover:bg-muted',
            )}
          >
            {r.label}
          </button>
        ))}
        <span className="ml-2 text-xs text-muted-foreground/60">
          Granularity: {tsData?.granularity ?? range.granularity}
        </span>
        {buckets.length > 0 && (
          <button
            onClick={exportCsv}
            className="ml-auto flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </button>
        )}
      </div>

      {/* Metric selector */}
      <div className="mb-4 flex flex-wrap gap-2">
        {METRIC_OPTIONS.map((m) => (
          <button
            key={m.key}
            onClick={() => setActiveMetric(m.key)}
            className={clsx(
              'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              m.key === activeMetric
                ? 'bg-indigo-600 text-white'
                : 'bg-muted/50 text-muted-foreground hover:bg-muted',
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Summary cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <SummaryCard label="Total" value={metricConfig.format(summary.total)} />
        <SummaryCard label="Average / Bucket" value={metricConfig.format(summary.avg)} />
        <SummaryCard label="Peak" value={metricConfig.format(summary.max)} highlight />
        <SummaryCard label="Buckets" value={String(buckets.length)} />
      </div>

      {/* Chart */}
      {isLoading ? (
        <AnalyticsSkeleton />
      ) : buckets.length === 0 ? (
        <EmptyState
          icon={BarChart3}
          title="No data available"
          description="No analytics data for this time range. Try selecting a wider window."
        />
      ) : (
        <BarChart buckets={buckets} metricKey={activeMetric} />
      )}

      {/* Provider comparison table */}
      {providers.length > 0 && (
        <ProviderTable providers={providers} />
      )}
    </div>
  );
}

function SummaryCard({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className={clsx('text-2xl font-bold', highlight ? 'text-primary' : 'text-foreground')}>
        {value}
      </p>
    </div>
  );
}

function BarChart({ buckets, metricKey }: { buckets: TimeSeriesBucket[]; metricKey: MetricKey }) {
  const values = buckets.map((b) => {
    const v = b[metricKey];
    return typeof v === 'number' ? v : 0;
  });
  const maxVal = Math.max(...values, 1);

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex h-48 items-end gap-px">
        {values.map((v, i) => {
          const pct = (v / maxVal) * 100;
          const bucket = buckets[i];
          const isAnomaly = v > maxVal * 0.85;
          return (
            <div
              key={i}
              className="group relative flex-1"
              title={`${formatBucketLabel(bucket.bucket)}: ${v}`}
            >
              <div
                className={clsx(
                  'w-full rounded-t transition-colors',
                  isAnomaly
                    ? 'bg-red-400 hover:bg-red-500'
                    : 'bg-primary/60 hover:bg-primary/100',
                )}
                style={{ height: `${Math.max(pct, 1)}%` }}
              />
              {/* Tooltip */}
              <div className="pointer-events-none absolute -top-10 left-1/2 z-10 hidden -translate-x-1/2 rounded bg-popover px-2 py-1 text-xs text-white whitespace-nowrap group-hover:block">
                {formatBucketLabel(bucket.bucket)}: {v}
              </div>
            </div>
          );
        })}
      </div>
      {/* X-axis labels */}
      <div className="mt-2 flex justify-between text-xs text-muted-foreground/60">
        <span>{formatBucketLabel(buckets[0]?.bucket ?? '')}</span>
        {buckets.length > 2 && (
          <span>{formatBucketLabel(buckets[Math.floor(buckets.length / 2)]?.bucket ?? '')}</span>
        )}
        <span>{formatBucketLabel(buckets[buckets.length - 1]?.bucket ?? '')}</span>
      </div>
    </div>
  );
}

function formatBucketLabel(bucket: string): string {
  if (!bucket) return '';
  const d = new Date(bucket);
  if (isNaN(d.getTime())) return bucket;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: 'numeric' });
}

function ProviderTable({ providers }: { providers: ProviderPerformance[] }) {
  return (
    <div className="mt-8 rounded-xl border border-border bg-card">
      <div className="border-b border-border px-6 py-4">
        <h2 className="text-lg font-semibold text-foreground">Provider Comparison</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3">Requests</th>
              <th className="px-4 py-3">Error Rate</th>
              <th className="px-4 py-3">Avg Latency</th>
              <th className="px-4 py-3">P95 Latency</th>
              <th className="px-4 py-3">Cost</th>
              <th className="px-4 py-3">Incidents</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {providers.map((p) => (
              <tr key={p.model} className="hover:bg-muted/50">
                <td className="px-4 py-3 text-sm font-medium text-foreground">{p.model}</td>
                <td className="px-4 py-3 text-sm text-muted-foreground">{p.totalRequests.toLocaleString()}</td>
                <td className="px-4 py-3">
                  <span
                    className={clsx(
                      'text-sm',
                      p.errorRate > 5 ? 'text-red-600' : p.errorRate > 1 ? 'text-yellow-600' : 'text-green-600',
                    )}
                  >
                    {p.errorRate.toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-muted-foreground">
                  {p.avgLatencyMs != null ? `${p.avgLatencyMs.toFixed(0)}ms` : '-'}
                </td>
                <td className="px-4 py-3 text-sm text-muted-foreground">
                  {p.p95LatencyMs != null ? `${p.p95LatencyMs.toFixed(0)}ms` : '-'}
                </td>
                <td className="px-4 py-3 text-sm text-muted-foreground">${p.totalCostUsd.toFixed(2)}</td>
                <td className="px-4 py-3">
                  <span
                    className={clsx(
                      'text-sm',
                      p.incidentCount > 10 ? 'text-red-600' : p.incidentCount > 0 ? 'text-yellow-600' : 'text-green-600',
                    )}
                  >
                    {p.incidentCount} ({p.incidentRate.toFixed(1)}%)
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
