'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getDashboardMetrics } from '@/lib/api';
import { CostAnalyticsSection } from '@/components/dashboard/CostAnalytics';
import { DetectionEfficacySection } from '@/components/dashboard/DetectionEfficacy';
import { SlaMetricsSection } from '@/components/dashboard/SlaMetrics';
import { Toast } from '@/components/ui/Toast';
import type { ToastItem } from '@/components/ui/Toast';
import type { RecentIncidentSummary } from '@/types';
import { SEVERITY_COLORS, STATUS_COLORS } from '@/lib/constants';
import { clsx } from 'clsx';

export default function DashboardPage() {
  const { user } = useAuth();
  const { status: wsStatus, lastEvent } = useWebSocket();
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard', 'metrics'],
    queryFn: getDashboardMetrics,
    refetchInterval: wsStatus === 'connected' ? undefined : 30_000,
  });

  // Toast for new critical/high incidents
  useEffect(() => {
    if (lastEvent?.type !== 'incident.new') return;
    const data = lastEvent.data as {
      severity?: string;
      title?: string;
      id?: string;
    };
    const severity = data.severity ?? 'info';
    if (severity === 'critical' || severity === 'high') {
      setToasts((prev) => [
        ...prev,
        {
          id: data.id ?? crypto.randomUUID(),
          message: `New ${severity} incident: ${data.title ?? 'Detection triggered'}`,
          severity,
        },
      ]);
    }
  }, [lastEvent]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <div>
      {/* Toast notifications */}
      {toasts.length > 0 && (
        <div className="fixed right-4 top-4 z-50 flex w-96 flex-col gap-2">
          {toasts.map((toast) => (
            <Toast
              key={toast.id}
              message={toast.message}
              severity={toast.severity}
              onDismiss={() => dismissToast(toast.id)}
            />
          ))}
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Welcome back, {user?.name ?? 'User'}
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total Incidents"
          value={isLoading ? '—' : String(metrics?.totalIncidents ?? 0)}
        />
        <MetricCard
          label="Open Incidents"
          value={isLoading ? '—' : String(metrics?.openIncidents ?? 0)}
          highlight={!!metrics?.openIncidents}
        />
        <SeverityBreakdownCard
          items={metrics?.incidentsBySeverity ?? []}
          isLoading={isLoading}
        />
        <StatusBreakdownCard
          items={metrics?.incidentsByStatus ?? []}
          isLoading={isLoading}
        />
      </div>

      {/* SLA metrics */}
      <SlaMetricsSection />

      {/* Cost analytics */}
      <CostAnalyticsSection />

      {/* Detection efficacy */}
      <DetectionEfficacySection />

      {/* Recent incidents */}
      <div className="mt-8 rounded-xl border border-border bg-card">
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

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : metrics?.recentIncidents.length ? (
          <IncidentTable incidents={metrics.recentIncidents} />
        ) : (
          <EmptyState />
        )}
      </div>
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
  isLoading,
}: {
  items: { severity: string; count: number }[];
  isLoading: boolean;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="mb-2 text-sm text-muted-foreground">By Severity</p>
      {isLoading ? (
        <p className="text-lg text-muted-foreground/50">—</p>
      ) : items.length === 0 ? (
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
  isLoading,
}: {
  items: { status: string; count: number }[];
  isLoading: boolean;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="mb-2 text-sm text-muted-foreground">By Status</p>
      {isLoading ? (
        <p className="text-lg text-muted-foreground/50">—</p>
      ) : items.length === 0 ? (
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
            <td className="px-6 py-3 text-sm text-muted-foreground">
              {new Date(inc.createdAt).toLocaleString()}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function EmptyState() {
  return (
    <div className="px-6 py-12 text-center">
      <p className="text-sm text-muted-foreground">No incidents yet</p>
      <p className="mt-1 text-xs text-muted-foreground/60">
        Incidents will appear here as your LLM traffic is analyzed
      </p>
    </div>
  );
}
