'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { listDiscoveries, getShadowAISummary, updateDiscoveryStatus } from '@/lib/api';
import type { ShadowAIDiscovery } from '@/lib/api';

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const STATUS_COLORS: Record<string, string> = {
  discovered: 'bg-yellow-100 text-yellow-700',
  monitored: 'bg-green-100 text-green-700',
  blocked: 'bg-red-100 text-red-700',
  approved: 'bg-blue-100 text-blue-700',
};

export default function ShadowAIPage() {
  const queryClient = useQueryClient();
  const [filterStatus, setFilterStatus] = useState('');
  const [filterRisk, setFilterRisk] = useState('');

  const { data: summary } = useQuery({
    queryKey: ['shadow-ai-summary'],
    queryFn: () => getShadowAISummary(30),
  });

  const { data, isLoading } = useQuery({
    queryKey: ['shadow-ai', filterStatus, filterRisk],
    queryFn: () =>
      listDiscoveries({
        status: filterStatus || undefined,
        riskLevel: filterRisk || undefined,
        limit: 100,
      }),
  });

  const items = data?.items ?? [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Shadow AI Discovery</h1>
        <p className="text-sm text-gray-500">
          Discover and manage unauthorized AI service usage across your organization
        </p>
      </div>

      {/* Coverage banner */}
      {summary && (
        <div
          className={clsx(
            'mb-6 rounded-xl border p-6',
            summary.coveragePct >= 90
              ? 'border-green-200 bg-green-50'
              : summary.coveragePct >= 70
                ? 'border-yellow-200 bg-yellow-50'
                : 'border-red-200 bg-red-50',
          )}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-gray-900">
                AI Traffic Coverage: {summary.coveragePct}%
              </p>
              <p className="mt-1 text-xs text-gray-600">
                {summary.totalMonitoredRequests.toLocaleString()} monitored requests ·{' '}
                {summary.totalUnmonitoredRequests.toLocaleString()} unmonitored requests
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">{summary.totalDiscovered}</p>
              <p className="text-xs text-gray-500">services discovered</p>
            </div>
          </div>
          {/* Coverage bar */}
          <div className="mt-3 h-2 w-full rounded-full bg-gray-200">
            <div
              className={clsx(
                'h-2 rounded-full transition-all',
                summary.coveragePct >= 90
                  ? 'bg-green-500'
                  : summary.coveragePct >= 70
                    ? 'bg-yellow-500'
                    : 'bg-red-500',
              )}
              style={{ width: `${Math.min(summary.coveragePct, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Summary cards */}
      {summary && (
        <div className="mb-6 grid grid-cols-4 gap-4">
          <StatCard label="Unmonitored" value={summary.unmonitoredCount} highlight />
          <StatCard label="Monitored" value={summary.monitoredCount} color="text-green-600" />
          <StatCard label="Blocked" value={summary.blockedCount} color="text-red-600" />
          <StatCard
            label="Providers"
            value={summary.byProvider.length}
          />
        </div>
      )}

      {/* Provider breakdown */}
      {summary && summary.byProvider.length > 0 && (
        <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">By Provider</h2>
          <div className="flex flex-wrap gap-3">
            {summary.byProvider.map((p) => (
              <div key={p.provider} className="rounded-lg border border-gray-100 px-4 py-2">
                <p className="text-sm font-medium text-gray-900">{p.provider}</p>
                <p className="text-xs text-gray-500">
                  {p.services} service{p.services !== 1 ? 's' : ''} · {p.requests.toLocaleString()} requests
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="discovered">Discovered</option>
          <option value="monitored">Monitored</option>
          <option value="blocked">Blocked</option>
          <option value="approved">Approved</option>
        </select>
        <select
          value={filterRisk}
          onChange={(e) => setFilterRisk(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All risk levels</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Discoveries table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
          <p className="text-sm text-gray-500">No AI services discovered yet</p>
          <p className="mt-1 text-xs text-gray-400">
            Configure network proxy integration to start discovering shadow AI usage
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3">Provider / Endpoint</th>
                <th className="px-4 py-3">Department</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Requests</th>
                <th className="px-4 py-3">Last Seen</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((d) => (
                <DiscoveryRow
                  key={d.id}
                  discovery={d}
                  onRefresh={() => {
                    queryClient.invalidateQueries({ queryKey: ['shadow-ai'] });
                    queryClient.invalidateQueries({ queryKey: ['shadow-ai-summary'] });
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  highlight,
  color,
}: {
  label: string;
  value: number;
  highlight?: boolean;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className={clsx('text-2xl font-bold', highlight ? 'text-yellow-600' : color ?? 'text-gray-900')}>
        {value}
      </p>
    </div>
  );
}

function DiscoveryRow({
  discovery,
  onRefresh,
}: {
  discovery: ShadowAIDiscovery;
  onRefresh: () => void;
}) {
  const mutation = useMutation({
    mutationFn: (newStatus: string) => updateDiscoveryStatus(discovery.id, newStatus),
    onSuccess: onRefresh,
  });

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-gray-900">{discovery.provider}</p>
        <p className="text-xs text-gray-500 truncate max-w-xs">{discovery.endpoint}</p>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">{discovery.department ?? '-'}</td>
      <td className="px-4 py-3">
        <span
          className={clsx(
            'rounded-full px-2 py-0.5 text-xs font-medium',
            RISK_COLORS[discovery.riskLevel] ?? 'bg-gray-100 text-gray-600',
          )}
        >
          {discovery.riskLevel}
        </span>
      </td>
      <td className="px-4 py-3">
        <span
          className={clsx(
            'rounded-full px-2 py-0.5 text-xs font-medium',
            STATUS_COLORS[discovery.status] ?? 'bg-gray-100 text-gray-600',
          )}
        >
          {discovery.status}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">
        {discovery.requestCount.toLocaleString()}
      </td>
      <td className="px-4 py-3 text-xs text-gray-500">
        {new Date(discovery.lastSeenAt).toLocaleDateString()}
      </td>
      <td className="px-4 py-3">
        <div className="flex gap-2">
          {discovery.status === 'discovered' && (
            <>
              <button
                onClick={() => mutation.mutate('approved')}
                disabled={mutation.isPending}
                className="text-xs font-medium text-green-600 hover:text-green-500"
              >
                Approve
              </button>
              <button
                onClick={() => mutation.mutate('blocked')}
                disabled={mutation.isPending}
                className="text-xs font-medium text-red-600 hover:text-red-500"
              >
                Block
              </button>
            </>
          )}
          {discovery.status === 'blocked' && (
            <button
              onClick={() => mutation.mutate('approved')}
              disabled={mutation.isPending}
              className="text-xs font-medium text-green-600 hover:text-green-500"
            >
              Approve
            </button>
          )}
          {discovery.status === 'approved' && (
            <button
              onClick={() => mutation.mutate('monitored')}
              disabled={mutation.isPending}
              className="text-xs font-medium text-primary-600 hover:text-primary-500"
            >
              Monitor
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
