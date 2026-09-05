'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  listRedTeamRuns,
  getRedTeamRun,
  getRedTeamStats,
  createRedTeamRun,
} from '@/lib/api';
import type { RedTeamRun } from '@/lib/api';
import { QueryError } from '@/components/ui/QueryError';
import { EmptyState } from '@/components/ui/EmptyState';
import { Shield } from 'lucide-react';

const CATEGORY_LABELS: Record<string, string> = {
  injection_resistance: 'Injection Resistance',
  extraction_resistance: 'Extraction Resistance',
  pii_leakage: 'PII Leakage',
  compliance_boundary: 'Compliance Boundary',
  jailbreak_resistance: 'Jailbreak Resistance',
};

function ResilienceGauge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-muted-foreground/60">N/A</span>;
  const color =
    score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : score >= 40 ? 'text-orange-600' : 'text-red-600';
  return <span className={clsx('text-lg font-bold', color)}>{score.toFixed(1)}%</span>;
}

export default function RedTeamPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [runName, setRunName] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

  const { data: stats } = useQuery({
    queryKey: ['red-team-stats'],
    queryFn: () => getRedTeamStats(90),
  });

  const { data: runs, isLoading, isError, refetch } = useQuery({
    queryKey: ['red-team-runs'],
    queryFn: () => listRedTeamRuns({ limit: 50 }),
  });

  const { data: detail } = useQuery({
    queryKey: ['red-team-detail', selectedId],
    queryFn: () => getRedTeamRun(selectedId!),
    enabled: !!selectedId,
  });

  const createMutation = useMutation({
    mutationFn: createRedTeamRun,
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['red-team-runs'] });
      queryClient.invalidateQueries({ queryKey: ['red-team-stats'] });
      setSelectedId(run.id);
      setShowCreate(false);
      setRunName('');
      setSelectedCategories([]);
    },
  });

  function toggleCategory(cat: string) {
    setSelectedCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat],
    );
  }

  const items = runs?.items ?? [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Red Team Testing</h1>
          <p className="text-sm text-muted-foreground">
            Automated adversarial testing against your AI security posture
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/100"
        >
          New Run
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Total Runs</p>
            <p className="text-2xl font-bold text-foreground">{stats.totalRuns}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Avg Resilience</p>
            <ResilienceGauge score={stats.avgResilience} />
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Total Findings</p>
            <p className="text-2xl font-bold text-orange-600">{stats.totalFindings}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Completed</p>
            <p className="text-2xl font-bold text-green-600">{stats.completedRuns}</p>
          </div>
        </div>
      )}

      {/* Category breakdown + trend */}
      {stats && (stats.byCategory.length > 0 || stats.resilienceTrend.length > 0) && (
        <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {stats.byCategory.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-4">
              <h2 className="mb-3 text-sm font-semibold text-foreground">Failure Rate by Category</h2>
              <div className="space-y-2">
                {stats.byCategory.map((c) => {
                  const failRate = c.total > 0 ? (c.failures / c.total * 100).toFixed(1) : '0.0';
                  return (
                    <div key={c.category} className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">{CATEGORY_LABELS[c.category] ?? c.category}</span>
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-20 rounded-full bg-muted">
                          <div
                            className="h-2 rounded-full bg-red-500"
                            style={{ width: `${Math.min(100, Number(failRate))}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium text-foreground">{failRate}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {stats.resilienceTrend.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-4">
              <h2 className="mb-3 text-sm font-semibold text-foreground">Resilience Trend</h2>
              <div className="space-y-2">
                {stats.resilienceTrend.map((t, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground truncate max-w-[200px]">{t.name}</span>
                    <ResilienceGauge score={t.score} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create run form */}
      {showCreate && (
        <div className="mb-6 rounded-xl border border-primary/20 bg-primary/10 p-6">
          <h2 className="mb-4 text-sm font-semibold text-foreground">Create Red Team Run</h2>
          <div className="mb-4">
            <label htmlFor="red-team-run-name" className="mb-1 block text-xs text-muted-foreground">Run Name</label>
            <input
              id="red-team-run-name"
              value={runName}
              onChange={(e) => setRunName(e.target.value)}
              placeholder="e.g. Weekly security assessment"
              className="w-full max-w-md rounded-lg border border-border px-3 py-2 text-sm"
            />
          </div>
          <fieldset className="mb-4">
            <legend className="mb-2 block text-xs text-muted-foreground">Test Categories</legend>
            <div className="flex flex-wrap gap-2">
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => toggleCategory(key)}
                  className={clsx(
                    'rounded-lg border px-3 py-1.5 text-xs transition-colors',
                    selectedCategories.includes(key)
                      ? 'border-primary/30 bg-primary/10 text-primary'
                      : 'border-border bg-card text-muted-foreground hover:bg-muted/50',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </fieldset>
          <button
            onClick={() =>
              createMutation.mutate({
                name: runName || `Run ${new Date().toLocaleDateString()}`,
                testCategories: selectedCategories.length > 0 ? selectedCategories : Object.keys(CATEGORY_LABELS),
              })
            }
            disabled={createMutation.isPending}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/100 disabled:opacity-50"
          >
            {createMutation.isPending ? 'Running Tests...' : 'Run Tests'}
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Runs list */}
        <div className="space-y-3">
          {isError ? (
            <QueryError message="Failed to load red team runs." onRetry={refetch} />
          ) : isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={Shield}
              title="No red team runs yet"
              description="Create an adversarial test run to evaluate your AI security posture."
              action={{ label: 'New Run', onClick: () => setShowCreate(true) }}
            />
          ) : (
            items.map((run: RedTeamRun) => (
              <button
                key={run.id}
                onClick={() => setSelectedId(run.id)}
                className={clsx(
                  'w-full rounded-xl border bg-card p-4 text-left transition-colors',
                  selectedId === run.id
                    ? 'border-primary/30 ring-1 ring-primary/20'
                    : 'border-border hover:border-border',
                )}
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-medium text-foreground">{run.name}</span>
                  <ResilienceGauge score={run.resilienceScore} />
                </div>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span
                    className={clsx(
                      'rounded px-1.5 py-0.5',
                      run.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700',
                    )}
                  >
                    {run.status}
                  </span>
                  <span>{run.totalTests} tests</span>
                  <span className="text-green-600">{run.passedTests} passed</span>
                  <span className="text-red-600">{run.failedTests} failed</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground/60">
                  {new Date(run.createdAt).toLocaleString()}
                </p>
              </button>
            ))
          )}
        </div>

        {/* Detail panel */}
        <div>
          {selectedId && detail ? (
            <div className="sticky top-4 space-y-4 rounded-xl border border-border bg-card p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-foreground">{detail.name}</h2>
                <ResilienceGauge score={detail.resilienceScore} />
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <p className="text-xs text-muted-foreground">Total</p>
                  <p className="text-lg font-bold text-foreground">{detail.totalTests}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Passed</p>
                  <p className="text-lg font-bold text-green-600">{detail.passedTests}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Failed</p>
                  <p className="text-lg font-bold text-red-600">{detail.failedTests}</p>
                </div>
              </div>

              <div className="max-h-96 space-y-2 overflow-y-auto">
                {detail.findings.map((f) => (
                  <div
                    key={f.id}
                    className={clsx(
                      'rounded-lg border p-3',
                      f.passed ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50',
                    )}
                  >
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-xs font-medium text-foreground">{f.testName}</span>
                      <span
                        className={clsx(
                          'rounded px-1.5 py-0.5 text-xs',
                          f.passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700',
                        )}
                      >
                        {f.passed ? 'PASS' : 'FAIL'}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {CATEGORY_LABELS[f.testCategory] ?? f.testCategory}
                    </p>
                    {f.explanation && (
                      <p className="mt-1 text-xs text-muted-foreground">{f.explanation}</p>
                    )}
                    {f.attackPrompt && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-xs text-muted-foreground/60">
                          View attack prompt
                        </summary>
                        <pre className="mt-1 max-h-24 overflow-auto rounded bg-muted p-2 text-xs text-foreground">
                          {f.attackPrompt}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center rounded-xl border border-border bg-card py-24">
              <p className="text-sm text-muted-foreground/60">Select a run to view findings</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
