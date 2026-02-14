'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useToast } from '@/hooks/useToast';
import { getDashboardMetrics, getRiskScore } from '@/lib/api';
import { Sparkline } from '@/components/charts/Sparkline';
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';
import { CostAnalyticsSection } from '@/components/dashboard/CostAnalytics';
import { DetectionEfficacySection } from '@/components/dashboard/DetectionEfficacy';
import { SlaMetricsSection } from '@/components/dashboard/SlaMetrics';
import { DashboardSkeleton } from '@/components/ui/Skeleton';
import { QueryError } from '@/components/ui/QueryError';
import type { RecentIncidentSummary } from '@/types';
import { SEVERITY_COLORS, STATUS_COLORS } from '@/lib/constants';
import { timeAgo } from '@/lib/format';
import { clsx } from 'clsx';

export default function DashboardPage() {
  const { user } = useAuth();
  const { status: wsStatus, lastEvent } = useWebSocket();
  const { toast } = useToast();

  const { data: metrics, isLoading, isError, refetch } = useQuery({
    queryKey: ['dashboard', 'metrics'],
    queryFn: getDashboardMetrics,
    refetchInterval: wsStatus === 'connected' ? undefined : 30_000,
  });

  const { data: riskData } = useQuery({
    queryKey: ['risk-score', 30],
    queryFn: () => getRiskScore(30),
  });

  // Toast for new critical/high incidents
  useEffect(() => {
    if (lastEvent?.type !== 'incident.new') return;
    const data = lastEvent.data as {
      severity?: string;
      title?: string;
    };
    const severity = data.severity ?? 'info';
    if (severity === 'critical' || severity === 'high') {
      toast(
        `New ${severity} incident: ${data.title ?? 'Detection triggered'}`,
        severity as 'critical' | 'high',
      );
    }
  }, [lastEvent, toast]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Welcome back, {user?.name ?? 'User'}
        </p>
      </div>

      {isError ? (
        <QueryError message="Failed to load dashboard metrics." onRetry={refetch} />
      ) : isLoading ? (
        <DashboardSkeleton />
      ) : (
        <>
          {/* Metric cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Total Incidents"
              value={String(metrics?.totalIncidents ?? 0)}
            />
            <MetricCard
              label="Open Incidents"
              value={String(metrics?.openIncidents ?? 0)}
              highlight={!!metrics?.openIncidents}
            />
            <SeverityBreakdownCard
              items={metrics?.incidentsBySeverity ?? []}
            />
            <StatusBreakdownCard
              items={metrics?.incidentsByStatus ?? []}
            />
          </div>

          {/* Risk score widget */}
          {riskData && riskData.totalIncidents > 0 && (
            <RiskWidget
              grade={riskData.grade}
              score={riskData.overallScore}
              trend={riskData.trendDirection}
              criticalOpen={riskData.criticalOpen}
              trendData={riskData.trend.map((p) => p.score)}
            />
          )}

          {/* SLA metrics */}
          <SlaMetricsSection />

          {/* Cost analytics */}
          <CostAnalyticsSection />

          {/* Detection efficacy */}
          <DetectionEfficacySection />

          {/* Recent incidents + Activity feed */}
          <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2 rounded-xl border border-border bg-card">
              <div className="flex items-center justify-between border-b border-border px-6 py-4">
                <h2 className="text-lg font-semibold text-foreground">
                  Recent Incidents
                </h2>
                <Link
                  href="/dashboard/incidents"
                  className="text-sm font-medium text-primary hover:text-primary"
                >
                  View all
                </Link>
              </div>

              {metrics?.recentIncidents.length ? (
                <div className="overflow-x-auto">
                  <IncidentTable incidents={metrics.recentIncidents} />
                </div>
              ) : (
                <DashboardEmptyState />
              )}
            </div>

            <ActivityFeed />
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p
        className={clsx(
          'mt-1 text-2xl font-semibold',
          highlight ? 'text-red-400' : 'text-foreground',
        )}
      >
        {value}
      </p>
    </div>
  );
}

function SeverityBreakdownCard({
  items,
}: {
  items: { severity: string; count: number }[];
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="mb-2 text-sm text-muted-foreground">By Severity</p>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground/50">No data</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <span
              key={item.severity}
              className={clsx(
                'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium',
                SEVERITY_COLORS[item.severity] ?? 'bg-muted text-muted-foreground',
              )}
            >
              {item.severity} {item.count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusBreakdownCard({
  items,
}: {
  items: { status: string; count: number }[];
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="mb-2 text-sm text-muted-foreground">By Status</p>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground/50">No data</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <span
              key={item.status}
              className={clsx(
                'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium',
                STATUS_COLORS[item.status] ?? 'bg-muted text-muted-foreground',
              )}
            >
              {item.status} {item.count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function IncidentTable({
  incidents,
}: {
  incidents: RecentIncidentSummary[];
}) {
  return (
    <table className="w-full">
      <thead>
        <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <th className="px-6 py-3">Title</th>
          <th className="px-6 py-3">Category</th>
          <th className="px-6 py-3">Severity</th>
          <th className="px-6 py-3">Status</th>
          <th className="px-6 py-3">Created</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border">
        {incidents.map((inc) => (
          <tr key={inc.id} className="hover:bg-muted/50">
            <td className="px-6 py-3 text-sm font-medium text-foreground">
              <Link
                href={`/dashboard/incidents/${inc.id}`}
                className="hover:text-primary"
              >
                {inc.title}
              </Link>
            </td>
            <td className="px-6 py-3 text-sm text-muted-foreground">
              {inc.category.replace('_', ' ')}
            </td>
            <td className="px-6 py-3">
              <span
                className={clsx(
                  'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                  SEVERITY_COLORS[inc.severity] ?? 'bg-muted text-muted-foreground',
                )}
              >
                {inc.severity}
              </span>
            </td>
            <td className="px-6 py-3">
              <span
                className={clsx(
                  'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                  STATUS_COLORS[inc.status] ?? 'bg-muted text-muted-foreground',
                )}
              >
                {inc.status}
              </span>
            </td>
            <td className="px-6 py-3 text-sm text-muted-foreground" title={new Date(inc.createdAt).toLocaleString()}>
              {timeAgo(inc.createdAt)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DashboardEmptyState() {
  return (
    <div className="px-6 py-12 text-center">
      <p className="text-sm text-muted-foreground">No incidents yet</p>
      <p className="mt-1 text-xs text-muted-foreground/60">
        Incidents will appear here as your LLM traffic is analyzed
      </p>
    </div>
  );
}

const GRADE_BG: Record<string, string> = {
  A: 'border-green-500/30 bg-green-500/10 text-green-500',
  B: 'border-blue-500/30 bg-blue-500/10 text-blue-500',
  C: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-500',
  D: 'border-orange-500/30 bg-orange-500/10 text-orange-500',
  F: 'border-red-500/30 bg-red-500/10 text-red-500',
};

const TREND_INFO: Record<string, { label: string; color: string; arrow: string }> = {
  improving: { label: 'Improving', color: 'text-green-500', arrow: '↓' },
  stable: { label: 'Stable', color: 'text-muted-foreground', arrow: '→' },
  degrading: { label: 'Degrading', color: 'text-red-500', arrow: '↑' },
};

function RiskWidget({
  grade,
  score,
  trend,
  criticalOpen,
  trendData,
}: {
  grade: string;
  score: number;
  trend: string;
  criticalOpen: number;
  trendData: number[];
}) {
  const t = TREND_INFO[trend] ?? TREND_INFO.stable;
  const sparkColor = trend === 'improving' ? '#22c55e' : trend === 'degrading' ? '#ef4444' : '#6366f1';
  return (
    <Link
      href="/dashboard/risk-score"
      className="mt-4 flex items-center gap-4 rounded-xl border border-border bg-card p-4 transition-colors hover:bg-muted/50"
    >
      <div
        className={clsx(
          'flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 text-xl font-bold',
          GRADE_BG[grade] ?? 'text-muted-foreground',
        )}
      >
        {grade}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">
            Risk Score: {score}/100
          </span>
          <span className={clsx('text-xs font-medium', t.color)}>
            {t.arrow} {t.label}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          30-day composite score (lower is better)
          {criticalOpen > 0 && (
            <span className="ml-2 text-red-400">
              {criticalOpen} critical open
            </span>
          )}
        </p>
      </div>
      {trendData.length >= 2 && (
        <div className="w-24 shrink-0">
          <Sparkline data={trendData} color={sparkColor} height={32} />
        </div>
      )}
      <span className="shrink-0 text-xs font-medium text-primary">View details →</span>
    </Link>
  );
}
