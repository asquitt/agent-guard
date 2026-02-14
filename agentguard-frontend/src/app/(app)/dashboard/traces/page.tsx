'use client';

import { useCallback, useEffect, useState } from 'react';
import { clsx } from 'clsx';
import { listTraces, getTrace } from '@/lib/api';
import type { TraceListItem, TraceDetail, TraceFilters } from '@/lib/api';
import { TableSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { FileSearch } from 'lucide-react';
import { HTTP_STATUS_COLORS, SEVERITY_COLORS } from '@/lib/constants';

function statusColor(code: number | null): string {
  if (code == null) return 'text-muted-foreground bg-muted/50';
  const prefix = String(Math.floor(code / 100));
  return HTTP_STATUS_COLORS[prefix] ?? 'text-muted-foreground bg-muted/50';
}

export default function TracesPage() {
  const [items, setItems] = useState<TraceListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<TraceFilters>({ skip: 0, limit: 50 });
  const [selected, setSelected] = useState<TraceDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchTraces = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listTraces(filters);
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchTraces();
  }, [fetchTraces]);

  async function openDetail(id: string) {
    setDetailLoading(true);
    try {
      const detail = await getTrace(id);
      setSelected(detail);
    } catch {
      /* ignore */
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Request Traces</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Inspect proxy requests, latency, costs, and linked incidents.
          </p>
        </div>
        <span className="text-sm text-muted-foreground/60">{total} total</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search path…"
          className="rounded-lg border border-border px-3 py-1.5 text-sm"
          onChange={(e) =>
            setFilters((f) => ({ ...f, q: e.target.value || undefined, skip: 0 }))
          }
        />
        <input
          type="text"
          placeholder="Model"
          className="rounded-lg border border-border px-3 py-1.5 text-sm"
          onChange={(e) =>
            setFilters((f) => ({ ...f, model: e.target.value || undefined, skip: 0 }))
          }
        />
        <select
          className="rounded-lg border border-border px-3 py-1.5 text-sm"
          onChange={(e) => {
            const v = e.target.value;
            setFilters((f) => ({
              ...f,
              hasIncidents: v === '' ? undefined : v === 'true',
              skip: 0,
            }));
          }}
        >
          <option value="">All requests</option>
          <option value="true">With incidents</option>
          <option value="false">No incidents</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">
                Time
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">
                Method
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">
                Path
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">
                Model
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">
                Latency
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">
                Tokens
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">
                Cost
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">
                Incidents
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              <tr>
                <td colSpan={9}>
                  <TableSkeleton rows={6} cols={9} />
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-4">
                  <EmptyState
                    icon={FileSearch}
                    title="No traces found"
                    description="No request traces match your filters."
                  />
                </td>
              </tr>
            ) : (
              items.map((t) => (
                <tr
                  key={t.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => openDetail(t.id)}
                >
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-muted-foreground">
                    {new Date(t.createdAt).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono font-medium text-foreground">
                    {t.method}
                  </td>
                  <td className="max-w-[200px] truncate px-4 py-3 text-xs text-foreground">
                    {t.path}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{t.model ?? '—'}</td>
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                        statusColor(t.statusCode),
                      )}
                    >
                      {t.statusCode ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {t.latencyMs != null ? `${t.latencyMs}ms` : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {t.inputTokens != null || t.outputTokens != null
                      ? `${t.inputTokens ?? 0}/${t.outputTokens ?? 0}`
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {t.costUsd != null ? `$${t.costUsd.toFixed(4)}` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {t.incidentCount > 0 ? (
                      <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                        {t.incidentCount}
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground/60">0</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > (filters.limit ?? 50) && (
        <nav aria-label="Traces pagination" className="flex items-center justify-between">
          <button
            disabled={(filters.skip ?? 0) === 0}
            aria-label="Go to previous page"
            onClick={() =>
              setFilters((f) => ({
                ...f,
                skip: Math.max(0, (f.skip ?? 0) - (f.limit ?? 50)),
              }))
            }
            className="rounded-lg border px-3 py-1.5 text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-muted-foreground">
            {(filters.skip ?? 0) + 1}–
            {Math.min((filters.skip ?? 0) + (filters.limit ?? 50), total)} of {total}
          </span>
          <button
            disabled={(filters.skip ?? 0) + (filters.limit ?? 50) >= total}
            aria-label="Go to next page"
            onClick={() =>
              setFilters((f) => ({
                ...f,
                skip: (f.skip ?? 0) + (f.limit ?? 50),
              }))
            }
            className="rounded-lg border px-3 py-1.5 text-sm disabled:opacity-40"
          >
            Next
          </button>
        </nav>
      )}

      {/* Detail slide-over */}
      {(selected || detailLoading) && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/30" role="dialog" aria-modal="true" aria-label="Trace detail">
          <div className="w-full max-w-2xl overflow-y-auto bg-card p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Trace Detail</h2>
              <button
                onClick={() => setSelected(null)}
                aria-label="Close trace detail"
                className="text-muted-foreground/60 hover:text-muted-foreground"
              >
                ✕
              </button>
            </div>

            {detailLoading ? (
              <div className="flex items-center justify-center py-16">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              </div>
            ) : selected ? (
              <div className="mt-4 space-y-6">
                {/* Meta */}
                <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
                  <div>
                    <span className="text-muted-foreground">Method</span>
                    <p className="font-mono font-medium">{selected.method}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Status</span>
                    <p>
                      <span
                        className={clsx(
                          'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                          statusColor(selected.statusCode),
                        )}
                      >
                        {selected.statusCode ?? '—'}
                      </span>
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Path</span>
                    <p className="font-mono text-xs break-all">{selected.path}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Model</span>
                    <p>{selected.model ?? '—'}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Latency</span>
                    <p>{selected.latencyMs != null ? `${selected.latencyMs}ms` : '—'}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Cost</span>
                    <p>{selected.costUsd != null ? `$${selected.costUsd.toFixed(4)}` : '—'}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Tokens (in/out)</span>
                    <p>
                      {selected.inputTokens ?? 0} / {selected.outputTokens ?? 0}
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Time</span>
                    <p>{new Date(selected.createdAt).toLocaleString()}</p>
                  </div>
                </div>

                {/* Request body */}
                {selected.requestBody && (
                  <div>
                    <h3 className="text-sm font-medium text-foreground">Request Body</h3>
                    <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-muted/50 p-3 text-xs">
                      {formatJson(selected.requestBody)}
                    </pre>
                  </div>
                )}

                {/* Response body */}
                {selected.responseBody && (
                  <div>
                    <h3 className="text-sm font-medium text-foreground">Response Body</h3>
                    <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-muted/50 p-3 text-xs">
                      {formatJson(selected.responseBody)}
                    </pre>
                  </div>
                )}

                {/* Linked incidents */}
                {selected.incidents.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-foreground">
                      Linked Incidents ({selected.incidents.length})
                    </h3>
                    <div className="mt-2 space-y-2">
                      {selected.incidents.map((inc) => (
                        <div
                          key={inc.id}
                          className="flex items-center justify-between rounded-lg border border-border px-4 py-2"
                        >
                          <div className="flex items-center gap-2">
                            <span
                              className={clsx(
                                'rounded-full px-2 py-0.5 text-xs font-medium',
                                SEVERITY_COLORS[inc.severity] ?? 'bg-muted text-foreground',
                              )}
                            >
                              {inc.severity}
                            </span>
                            <span className="text-sm text-foreground">{inc.title}</span>
                          </div>
                          <span className="text-xs text-muted-foreground/60">{inc.category}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function formatJson(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}
