'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  listIndicators,
  getThreatSummary,
  updateIndicator,
  seedPlatformIndicators,
} from '@/lib/api';
import type { ThreatIndicator } from '@/lib/api';

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-green-100 text-green-700',
};

const TYPE_LABELS: Record<string, string> = {
  injection_pattern: 'Injection',
  jailbreak: 'Jailbreak',
  extraction: 'Extraction',
  exfiltration: 'Exfiltration',
  social_engineering: 'Social Engineering',
  mcp_exploit: 'MCP Exploit',
  tool_abuse: 'Tool Abuse',
};

export default function ThreatIntelPage() {
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');

  const { data: summary } = useQuery({
    queryKey: ['threat-summary'],
    queryFn: () => getThreatSummary(30),
  });

  const { data: indicators, isLoading } = useQuery({
    queryKey: ['threat-indicators', typeFilter, severityFilter],
    queryFn: () =>
      listIndicators({
        indicatorType: typeFilter || undefined,
        severity: severityFilter || undefined,
        limit: 100,
      }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      updateIndicator(id, { isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threat-indicators'] });
      queryClient.invalidateQueries({ queryKey: ['threat-summary'] });
    },
  });

  const seedMutation = useMutation({
    mutationFn: seedPlatformIndicators,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threat-indicators'] });
      queryClient.invalidateQueries({ queryKey: ['threat-summary'] });
    },
  });

  const items = indicators?.items ?? [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Threat Intelligence</h1>
          <p className="text-sm text-gray-500">
            Attack patterns, emerging threats, and detection indicators
          </p>
        </div>
        <button
          onClick={() => seedMutation.mutate()}
          disabled={seedMutation.isPending}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500 disabled:opacity-50"
        >
          {seedMutation.isPending ? 'Seeding...' : 'Seed Platform Indicators'}
        </button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="mb-6 grid grid-cols-4 gap-4">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Total Indicators</p>
            <p className="text-2xl font-bold text-gray-900">{summary.totalIndicators}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Active</p>
            <p className="text-2xl font-bold text-green-600">{summary.activeIndicators}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Total Hits</p>
            <p className="text-2xl font-bold text-red-600">{summary.totalHits.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Threat Types</p>
            <p className="text-2xl font-bold text-gray-900">{summary.byType.length}</p>
          </div>
        </div>
      )}

      {/* Type breakdown + top indicators */}
      {summary && (
        <div className="mb-6 grid grid-cols-2 gap-4">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-900">By Type</h2>
            <div className="space-y-2">
              {summary.byType.map((t) => (
                <div key={t.type} className="flex items-center justify-between">
                  <span className="text-xs text-gray-600">{TYPE_LABELS[t.type] ?? t.type}</span>
                  <span className="text-xs font-medium text-gray-900">{t.count}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-900">Top Indicators by Hits</h2>
            <div className="space-y-2">
              {summary.topIndicators.length === 0 ? (
                <p className="text-xs text-gray-400">No hits recorded yet</p>
              ) : (
                summary.topIndicators.map((t, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={clsx('rounded px-1.5 py-0.5 text-xs', SEVERITY_COLORS[t.severity])}>
                        {t.severity}
                      </span>
                      <span className="text-xs text-gray-700">{t.name}</span>
                    </div>
                    <span className="text-xs font-medium text-gray-900">{t.hits}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All Types</option>
          <option value="injection_pattern">Injection</option>
          <option value="jailbreak">Jailbreak</option>
          <option value="extraction">Extraction</option>
          <option value="exfiltration">Exfiltration</option>
          <option value="social_engineering">Social Engineering</option>
          <option value="mcp_exploit">MCP Exploit</option>
          <option value="tool_abuse">Tool Abuse</option>
        </select>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Indicators table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
          <p className="text-sm text-gray-500">No indicators found. Click &quot;Seed Platform Indicators&quot; to get started.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Severity</th>
                <th className="px-4 py-3 font-medium">Confidence</th>
                <th className="px-4 py-3 font-medium">Hits</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Active</th>
              </tr>
            </thead>
            <tbody>
              {items.map((ind: ThreatIndicator) => (
                <tr key={ind.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{ind.name}</p>
                    {ind.description && (
                      <p className="mt-0.5 text-xs text-gray-500 line-clamp-1">{ind.description}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                      {TYPE_LABELS[ind.indicatorType] ?? ind.indicatorType}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={clsx('rounded px-2 py-0.5 text-xs', SEVERITY_COLORS[ind.severity])}>
                      {ind.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {(ind.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {ind.hitCount.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{ind.source}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() =>
                        toggleMutation.mutate({ id: ind.id, isActive: !ind.isActive })
                      }
                      className={clsx(
                        'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                        ind.isActive ? 'bg-primary-600' : 'bg-gray-300',
                      )}
                    >
                      <span
                        className={clsx(
                          'inline-block h-3 w-3 rounded-full bg-white transition-transform',
                          ind.isActive ? 'translate-x-5' : 'translate-x-1',
                        )}
                      />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
