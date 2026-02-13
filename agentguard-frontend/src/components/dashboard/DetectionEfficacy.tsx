'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { getDetectionEfficacy } from '@/lib/api';

const CATEGORY_LABELS: Record<string, string> = {
  pii_leak: 'PII Leak',
  compliance: 'Compliance',
  prompt_injection: 'Prompt Injection',
  prompt_extraction: 'Prompt Extraction',
  hallucination: 'Hallucination',
  cost_anomaly: 'Cost Anomaly',
  loop: 'Loop Detection',
  toxicity: 'Toxicity & Bias',
  tool_call: 'Tool Call Validation',
  mcp_security: 'MCP Security',
};

export function DetectionEfficacySection() {
  const [days, setDays] = useState(30);

  const { data, isLoading } = useQuery({
    queryKey: ['detectionEfficacy', days],
    queryFn: () => getDetectionEfficacy(days),
    refetchInterval: 60_000,
  });

  return (
    <div className="mb-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Detection Efficacy</h2>
        <div className="flex gap-1 rounded-lg bg-muted p-0.5">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={clsx(
                'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                days === d ? 'bg-card text-foreground shadow-sm shadow-black/10' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : !data || data.categories.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          No detection data for this period
        </div>
      ) : (
        <>
          {/* Overall FP rate card */}
          <div className="mb-4 rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs font-medium text-muted-foreground">Overall False Positive Rate</p>
                <p className={clsx(
                  'text-2xl font-bold',
                  data.overallFalsePositiveRate > 0.3 ? 'text-red-600' :
                  data.overallFalsePositiveRate > 0.1 ? 'text-yellow-600' : 'text-green-600',
                )}>
                  {(data.overallFalsePositiveRate * 100).toFixed(1)}%
                </p>
              </div>
              <div className="ml-auto text-right">
                <p className="text-xs font-medium text-muted-foreground">Total Detections</p>
                <p className="text-2xl font-bold text-foreground">
                  {data.categories.reduce((sum, c) => sum + c.total, 0)}
                </p>
              </div>
            </div>
          </div>

          {/* Per-category table */}
          <div className="rounded-xl border border-border bg-card">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">Resolved</th>
                  <th className="px-4 py-3">Dismissed</th>
                  <th className="px-4 py-3">FP Rate</th>
                  <th className="px-4 py-3">Avg Resolve Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.categories.map((cat) => (
                  <tr key={cat.category} className="hover:bg-muted/50">
                    <td className="px-4 py-3 text-sm font-medium text-foreground">
                      {CATEGORY_LABELS[cat.category] ?? cat.category}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{cat.total}</td>
                    <td className="px-4 py-3 text-sm text-green-600">{cat.resolved}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{cat.dismissed}</td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                        cat.falsePositiveRate > 0.3 ? 'bg-red-100 text-red-700' :
                        cat.falsePositiveRate > 0.1 ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700',
                      )}>
                        {(cat.falsePositiveRate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {cat.meanTimeToResolveHours != null
                        ? `${cat.meanTimeToResolveHours.toFixed(1)}h`
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
