'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { getRiskScore } from '@/lib/api';
import type { CategoryRisk } from '@/lib/api';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { QueryError } from '@/components/ui/QueryError';
import { TrendChart } from '@/components/charts/TrendChart';
import { ShieldCheck } from 'lucide-react';
import { TREND_COLORS } from '@/lib/constants';

const TIME_RANGES = [
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
] as const;

const GRADE_COLORS: Record<string, string> = {
  A: 'text-green-500 border-green-500/30 bg-green-500/10',
  B: 'text-blue-500 border-blue-500/30 bg-blue-500/10',
  C: 'text-yellow-500 border-yellow-500/30 bg-yellow-500/10',
  D: 'text-orange-500 border-orange-500/30 bg-orange-500/10',
  F: 'text-red-500 border-red-500/30 bg-red-500/10',
};

const TREND_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  improving: { label: 'Improving', color: 'text-green-500', icon: '↓' },
  stable: { label: 'Stable', color: 'text-muted-foreground', icon: '→' },
  degrading: { label: 'Degrading', color: 'text-red-500', icon: '↑' },
};

const CATEGORY_LABELS: Record<string, string> = {
  hallucination: 'Hallucination',
  pii_leak: 'PII Leak',
  financial_pii: 'Financial PII',
  compliance: 'Compliance',
  cost_anomaly: 'Cost Anomaly',
  loop: 'Loop Detection',
  prompt_injection: 'Prompt Injection',
  prompt_extraction: 'Prompt Extraction',
  jailbreak: 'Jailbreak',
  instruction_hierarchy: 'Instruction Hierarchy',
  toxicity: 'Toxicity & Bias',
  tool_call: 'Tool Call',
  mcp_security: 'MCP Security',
  schema_injection: 'Schema Injection',
  memory_exfiltration: 'Memory Exfil',
  sycophancy: 'Sycophancy',
  scope_enforcement: 'Scope Enforcement',
  sequential_action: 'Sequential Action',
  reasoning_trace: 'Reasoning Trace',
  confidence_hallucination: 'Confidence Hallucination',
  model_safety_profile: 'Model Safety',
  capability_monitor: 'Capability Monitor',
};

export default function RiskScorePage() {
  const [rangeIdx, setRangeIdx] = useState(1); // 30d default
  const range = TIME_RANGES[rangeIdx];

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['risk-score', range.days],
    queryFn: () => getRiskScore(range.days),
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Risk Score</h1>
          <p className="text-sm text-muted-foreground">
            Composite security posture for your organization
          </p>
        </div>
        <div className="flex items-center gap-2">
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
        </div>
      </div>

      {isError ? (
        <QueryError message="Failed to load risk score data." onRetry={refetch} />
      ) : isLoading ? (
        <RiskSkeleton />
      ) : !data || data.totalIncidents === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="No risk data yet"
          description="Risk scoring requires incident data. Start proxying LLM traffic to see your security posture."
          hints={[
            { label: 'View incidents', href: '/dashboard/incidents' },
            { label: 'Configure detectors', href: '/dashboard/detectors' },
          ]}
        />
      ) : (
        <>
          {/* Score + summary row */}
          <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-4">
            {/* Grade card */}
            <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-card p-6">
              <div
                className={clsx(
                  'flex h-20 w-20 items-center justify-center rounded-full border-4 text-4xl font-bold',
                  GRADE_COLORS[data.grade] ?? 'text-muted-foreground',
                )}
              >
                {data.grade}
              </div>
              <p className="mt-3 text-2xl font-bold text-foreground">
                {data.overallScore}
              </p>
              <p className="text-xs text-muted-foreground">out of 100 (lower is better)</p>
            </div>

            {/* Summary stats */}
            <StatCard label="Total Incidents" value={data.totalIncidents} />
            <StatCard label="Open Incidents" value={data.openIncidents} highlight={data.openIncidents > 0} />
            <div className="rounded-xl border border-border bg-card p-5">
              <p className="text-sm text-muted-foreground">Trend</p>
              <div className="mt-1 flex items-center gap-2">
                <span className={clsx('text-2xl font-semibold', TREND_LABELS[data.trendDirection]?.color)}>
                  {TREND_LABELS[data.trendDirection]?.icon}
                </span>
                <span className={clsx('text-lg font-semibold', TREND_LABELS[data.trendDirection]?.color)}>
                  {TREND_LABELS[data.trendDirection]?.label}
                </span>
              </div>
              {data.criticalOpen > 0 && (
                <p className="mt-1 text-xs text-red-400">
                  {data.criticalOpen} critical open
                </p>
              )}
            </div>
          </div>

          {/* Risk trend chart */}
          {data.trend.length > 1 && (
            <div className="mb-6 rounded-xl border border-border bg-card p-6">
              <h2 className="mb-4 text-sm font-semibold text-foreground">
                Risk Trend
              </h2>
              <TrendChart
                data={data.trend.map((p) => ({
                  label: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
                  value: p.score,
                }))}
                color={TREND_COLORS[data.trendDirection] ?? TREND_COLORS.stable}
                height={200}
              />
            </div>
          )}

          {/* Category heatmap */}
          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="mb-4 text-sm font-semibold text-foreground">
              Risk by Detection Category
            </h2>
            <div className="space-y-2">
              {data.categories.map((cat) => (
                <CategoryBar key={cat.category} category={cat} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={clsx('mt-1 text-2xl font-semibold', highlight ? 'text-red-400' : 'text-foreground')}>
        {value}
      </p>
    </div>
  );
}

function CategoryBar({ category }: { category: CategoryRisk }) {
  const label = CATEGORY_LABELS[category.category] ?? category.category;
  const barWidth = Math.max(category.score, 2);

  const barColor =
    category.score >= 70
      ? 'bg-red-500'
      : category.score >= 40
        ? 'bg-orange-500'
        : category.score >= 15
          ? 'bg-yellow-500'
          : 'bg-green-500';

  return (
    <div className="flex items-center gap-3">
      <span className="w-40 shrink-0 text-xs text-muted-foreground truncate">
        {label}
      </span>
      <div className="flex-1">
        <div className="h-5 w-full rounded-full bg-muted/50">
          <div
            className={clsx('h-5 rounded-full transition-all', barColor)}
            style={{ width: `${barWidth}%` }}
          />
        </div>
      </div>
      <span className="w-10 text-right text-xs font-medium text-foreground">
        {category.score}
      </span>
      <div className="flex w-32 gap-2 text-xs text-muted-foreground">
        <span>{category.incidentCount} total</span>
        {category.openCount > 0 && (
          <span className="text-red-400">{category.openCount} open</span>
        )}
      </div>
    </div>
  );
}

function RiskSkeleton() {
  return (
    <div>
      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="flex flex-col items-center rounded-xl border border-border bg-card p-6">
          <Skeleton className="h-20 w-20 rounded-full" />
          <Skeleton className="mt-3 h-7 w-12" />
          <Skeleton className="mt-1 h-3 w-32" />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-5">
            <Skeleton className="mb-2 h-4 w-24" />
            <Skeleton className="h-8 w-12" />
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-border bg-card p-6">
        <Skeleton className="mb-4 h-4 w-48" />
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-5 flex-1 rounded-full" />
              <Skeleton className="h-4 w-8" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
