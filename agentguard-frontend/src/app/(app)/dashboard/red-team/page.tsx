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

const CATEGORY_LABELS: Record<string, string> = {
  injection_resistance: 'Injection Resistance',
  extraction_resistance: 'Extraction Resistance',
  pii_leakage: 'PII Leakage',
  compliance_boundary: 'Compliance Boundary',
  jailbreak_resistance: 'Jailbreak Resistance',
};

function ResilienceGauge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-gray-400">N/A</span>;
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

  const { data: runs, isLoading } = useQuery({
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
          <h1 className="text-2xl font-bold text-gray-900">Red Team Testing</h1>
          <p className="text-sm text-gray-500">
            Automated adversarial testing against your AI security posture
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500"
        >
          New Run
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="mb-6 grid grid-cols-4 gap-4">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Total Runs</p>
            <p className="text-2xl font-bold text-gray-900">{stats.totalRuns}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Avg Resilience</p>
            <ResilienceGauge score={stats.avgResilience} />
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Total Findings</p>
            <p className="text-2xl font-bold text-orange-600">{stats.totalFindings}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Completed</p>
            <p className="text-2xl font-bold text-green-600">{stats.completedRuns}</p>
          </div>
        </div>
      )}

      {/* Category breakdown + trend */}
      {stats && (stats.byCategory.length > 0 || stats.resilienceTrend.length > 0) && (
        <div className="mb-6 grid grid-cols-2 gap-4">
          {stats.byCategory.length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <h2 className="mb-3 text-sm font-semibold text-gray-900">Failure Rate by Category</h2>
              <div className="space-y-2">
                {stats.byCategory.map((c) => {
                  const failRate = c.total > 0 ? (c.failures / c.total * 100).toFixed(1) : '0.0';
                  return (
                    <div key={c.category} className="flex items-center justify-between">
                      <span className="text-xs text-gray-600">{CATEGORY_LABELS[c.category] ?? c.category}</span>
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-20 rounded-full bg-gray-200">
                          <div
                            className="h-2 rounded-full bg-red-500"
                            style={{ width: `${Math.min(100, Number(failRate))}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium text-gray-900">{failRate}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {stats.resilienceTrend.length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <h2 className="mb-3 text-sm font-semibold text-gray-900">Resilience Trend</h2>
              <div className="space-y-2">
                {stats.resilienceTrend.map((t, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-xs text-gray-600 truncate max-w-[200px]">{t.name}</span>
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
        <div className="mb-6 rounded-xl border border-primary-200 bg-primary-50 p-6">
          <h2 className="mb-4 text-sm font-semibold text-gray-900">Create Red Team Run</h2>
          <div className="mb-4">
            <label className="mb-1 block text-xs text-gray-500">Run Name</label>
            <input
              value={runName}
              onChange={(e) => setRunName(e.target.value)}
              placeholder="e.g. Weekly security assessment"
              className="w-full max-w-md rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="mb-4">
            <label className="mb-2 block text-xs text-gray-500">Test Categories</label>
            <div className="flex flex-wrap gap-2">
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => toggleCategory(key)}
                  className={clsx(
                    'rounded-lg border px-3 py-1.5 text-xs transition-colors',
                    selectedCategories.includes(key)
                      ? 'border-primary-300 bg-primary-100 text-primary-700'
                      : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={() =>
              createMutation.mutate({
                name: runName || `Run ${new Date().toLocaleDateString()}`,
                testCategories: selectedCategories.length > 0 ? selectedCategories : Object.keys(CATEGORY_LABELS),
              })
            }
            disabled={createMutation.isPending}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500 disabled:opacity-50"
          >
            {createMutation.isPending ? 'Running Tests...' : 'Run Tests'}
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Runs list */}
        <div className="space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
              <p className="text-sm text-gray-500">No red team runs yet. Create one to get started.</p>
            </div>
          ) : (
            items.map((run: RedTeamRun) => (
              <button
                key={run.id}
                onClick={() => setSelectedId(run.id)}
                className={clsx(
                  'w-full rounded-xl border bg-white p-4 text-left transition-colors',
                  selectedId === run.id
                    ? 'border-primary-300 ring-1 ring-primary-200'
                    : 'border-gray-200 hover:border-gray-300',
                )}
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">{run.name}</span>
                  <ResilienceGauge score={run.resilienceScore} />
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
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
                <p className="mt-1 text-xs text-gray-400">
                  {new Date(run.createdAt).toLocaleString()}
                </p>
              </button>
            ))
          )}
        </div>

        {/* Detail panel */}
        <div>
          {selectedId && detail ? (
            <div className="sticky top-4 space-y-4 rounded-xl border border-gray-200 bg-white p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-900">{detail.name}</h2>
                <ResilienceGauge score={detail.resilienceScore} />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <p className="text-xs text-gray-500">Total</p>
                  <p className="text-lg font-bold text-gray-900">{detail.totalTests}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Passed</p>
                  <p className="text-lg font-bold text-green-600">{detail.passedTests}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Failed</p>
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
                      <span className="text-xs font-medium text-gray-900">{f.testName}</span>
                      <span
                        className={clsx(
                          'rounded px-1.5 py-0.5 text-xs',
                          f.passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700',
                        )}
                      >
                        {f.passed ? 'PASS' : 'FAIL'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      {CATEGORY_LABELS[f.testCategory] ?? f.testCategory}
                    </p>
                    {f.explanation && (
                      <p className="mt-1 text-xs text-gray-600">{f.explanation}</p>
                    )}
                    {f.attackPrompt && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-xs text-gray-400">
                          View attack prompt
                        </summary>
                        <pre className="mt-1 max-h-24 overflow-auto rounded bg-gray-100 p-2 text-xs text-gray-700">
                          {f.attackPrompt}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center rounded-xl border border-gray-200 bg-white py-24">
              <p className="text-sm text-gray-400">Select a run to view findings</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
