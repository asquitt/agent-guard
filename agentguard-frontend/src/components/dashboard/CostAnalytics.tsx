'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { getCostAnalytics } from '@/lib/api';
import { clsx } from 'clsx';
import type { CostAnalytics, CostByModel, DailyCost } from '@/types';

const PERIOD_OPTIONS = [
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
] as const;

function formatCost(cost: number): string {
  return cost < 0.01 && cost > 0 ? '<$0.01' : `$${cost.toFixed(2)}`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return String(tokens);
}

export function CostAnalyticsSection() {
  const [days, setDays] = useState(30);

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard', 'cost-analytics', days],
    queryFn: () => getCostAnalytics(days),
    refetchInterval: 60_000,
  });

  return (
    <div className="mt-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Cost Analytics</h2>
        <div className="flex gap-1 rounded-lg border border-border bg-card p-0.5">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.days}
              onClick={() => setDays(opt.days)}
              className={clsx(
                'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                days === opt.days
                  ? 'bg-primary text-white'
                  : 'text-muted-foreground hover:bg-muted',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          label="Total Cost"
          value={isLoading ? '—' : formatCost(data?.totalCost ?? 0)}
          highlight
        />
        <SummaryCard
          label="Total Requests"
          value={isLoading ? '—' : String(data?.totalRequests ?? 0)}
        />
        <SummaryCard
          label="Input Tokens"
          value={isLoading ? '—' : formatTokens(data?.totalInputTokens ?? 0)}
        />
        <SummaryCard
          label="Output Tokens"
          value={isLoading ? '—' : formatTokens(data?.totalOutputTokens ?? 0)}
        />
      </div>

      {/* Cost by model + daily trend */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CostByModelTable models={data?.costByModel ?? []} isLoading={isLoading} />
        <DailyCostChart dailyCosts={data?.dailyCosts ?? []} isLoading={isLoading} />
      </div>
    </div>
  );
}

function SummaryCard({
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
          highlight ? 'text-primary' : 'text-foreground',
        )}
      >
        {value}
      </p>
    </div>
  );
}

function CostByModelTable({
  models,
  isLoading,
}: {
  models: CostByModel[];
  isLoading: boolean;
}) {
  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="border-b border-border px-6 py-4">
        <h3 className="text-sm font-semibold text-foreground">Cost by Model</h3>
      </div>
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : models.length === 0 ? (
        <p className="px-6 py-8 text-center text-sm text-muted-foreground/60">No proxy requests yet</p>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
              <th className="px-6 py-2">Model</th>
              <th className="px-6 py-2 text-right">Cost</th>
              <th className="px-6 py-2 text-right">Requests</th>
              <th className="px-6 py-2 text-right">Tokens</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {models.map((m) => (
              <tr key={m.model} className="hover:bg-muted/50">
                <td className="px-6 py-2 text-sm font-medium text-foreground">{m.model}</td>
                <td className="px-6 py-2 text-right text-sm text-foreground">{formatCost(m.cost)}</td>
                <td className="px-6 py-2 text-right text-sm text-muted-foreground">{m.requests}</td>
                <td className="px-6 py-2 text-right text-sm text-muted-foreground">
                  {formatTokens(m.inputTokens + m.outputTokens)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function DailyCostChart({
  dailyCosts,
  isLoading,
}: {
  dailyCosts: DailyCost[];
  isLoading: boolean;
}) {
  const maxCost = Math.max(...dailyCosts.map((d) => d.cost), 0.01);

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="border-b border-border px-6 py-4">
        <h3 className="text-sm font-semibold text-foreground">Daily Cost Trend</h3>
      </div>
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : dailyCosts.length === 0 ? (
        <p className="px-6 py-8 text-center text-sm text-muted-foreground/60">No cost data yet</p>
      ) : (
        <div className="flex items-end gap-px px-6 py-4" style={{ height: 160 }}>
          {dailyCosts.map((d) => {
            const pct = maxCost > 0 ? (d.cost / maxCost) * 100 : 0;
            const dateLabel = new Date(d.date).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
            });
            return (
              <div
                key={d.date}
                className="group relative flex flex-1 flex-col items-center justify-end"
                style={{ height: '100%' }}
              >
                <div
                  className="w-full min-w-[4px] rounded-t bg-primary/100 transition-colors group-hover:bg-primary"
                  style={{ height: `${Math.max(pct, 2)}%` }}
                />
                {/* Tooltip */}
                <div className="pointer-events-none absolute -top-10 z-10 hidden whitespace-nowrap rounded bg-popover px-2 py-1 text-xs text-white group-hover:block">
                  {dateLabel}: {formatCost(d.cost)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
