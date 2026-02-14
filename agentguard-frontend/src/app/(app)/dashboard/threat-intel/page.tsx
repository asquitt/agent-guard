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
          <h1 className="text-2xl font-bold text-foreground">Threat Intelligence</h1>
          <p className="text-sm text-muted-foreground">
            Attack patterns, emerging threats, and detection indicators
          </p>
        </div>
        <button
          onClick={() => seedMutation.mutate()}
          disabled={seedMutation.isPending}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/100 disabled:opacity-50"
        >
          {seedMutation.isPending ? 'Seeding...' : 'Seed Platform Indicators'}
        </button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Total Indicators</p>
            <p className="text-2xl font-bold text-foreground">{summary.totalIndicators}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Active</p>
            <p className="text-2xl font-bold text-green-600">{summary.activeIndicators}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Total Hits</p>
            <p className="text-2xl font-bold text-red-600">{summary.totalHits.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Threat Types</p>
            <p className="text-2xl font-bold text-foreground">{summary.byType.length}</p>
          </div>
        </div>
      )}

      {/* Type breakdown + top indicators */}
      {summary && (
        <div className="mb-6 grid grid-cols-2 gap-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <h2 className="mb-3 text-sm font-semibold text-foreground">By Type</h2>
            <div className="space-y-2">
              {summary.byType.map((t) => (
                <div key={t.type} className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{TYPE_LABELS[t.type] ?? t.type}</span>
                  <span className="text-xs font-medium text-foreground">{t.count}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <h2 className="mb-3 text-sm font-semibold text-foreground">Top Indicators by Hits</h2>
            <div className="space-y-2">
              {summary.topIndicators.length === 0 ? (
                <p className="text-xs text-muted-foreground/60">No hits recorded yet</p>
              ) : (
                summary.topIndicators.map((t, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={clsx('rounded px-1.5 py-0.5 text-xs', SEVERITY_COLORS[t.severity])}>
                        {t.severity}
                      </span>
                      <span className="text-xs text-foreground">{t.name}</span>
                    </div>
                    <span className="text-xs font-medium text-foreground">{t.hits}</span>
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
          className="rounded-lg border border-border px-3 py-2 text-sm"
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
          className="rounded-lg border border-border px-3 py-2 text-sm"
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
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">No indicators found. Click &quot;Seed Platform Indicators&quot; to get started.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
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
                <tr key={ind.id} className="border-b border-border hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-foreground">{ind.name}</p>
                    {ind.description && (
                      <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">{ind.description}</p>
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
                  <td className="px-4 py-3 text-muted-foreground">
                    {(ind.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-3 font-medium text-foreground">
                    {ind.hitCount.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{ind.source}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() =>
                        toggleMutation.mutate({ id: ind.id, isActive: !ind.isActive })
                      }
                      className={clsx(
                        'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                        ind.isActive ? 'bg-primary' : 'bg-muted',
                      )}
                    >
                      <span
                        className={clsx(
                          'inline-block h-3 w-3 rounded-full bg-card transition-transform',
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
