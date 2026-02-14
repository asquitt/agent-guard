'use client';

import { useCallback, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { clsx } from 'clsx';
import { listIncidents, bulkUpdateStatus } from '@/lib/api';
import type { Incident, IncidentFilters } from '@/types';
import { SEVERITY_COLORS, STATUS_COLORS } from '@/lib/constants';
import { TableSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { QueryError } from '@/components/ui/QueryError';
import { ShieldAlert, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { timeAgo } from '@/lib/format';

type SortField = 'title' | 'category' | 'severity' | 'status' | 'createdAt';
type SortDir = 'asc' | 'desc';

const SEVERITY_ORDER: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };
const STATUS_ORDER: Record<string, number> = { open: 3, acknowledged: 2, resolved: 1, dismissed: 0 };

const PAGE_SIZE = 20;

export default function IncidentsPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<IncidentFilters>({ limit: PAGE_SIZE });
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<SortField>('createdAt');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['incidents', filters],
    queryFn: () => listIncidents(filters),
  });

  const bulkMutation = useMutation({
    mutationFn: ({ ids, status }: { ids: string[]; status: string }) =>
      bulkUpdateStatus(ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      setSelected(new Set());
    },
  });

  const rawIncidents = data?.items ?? [];

  const incidents = useMemo(() => {
    const sorted = [...rawIncidents];
    sorted.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'title':
          cmp = a.title.localeCompare(b.title);
          break;
        case 'category':
          cmp = a.category.localeCompare(b.category);
          break;
        case 'severity':
          cmp = (SEVERITY_ORDER[a.severity] ?? 0) - (SEVERITY_ORDER[b.severity] ?? 0);
          break;
        case 'status':
          cmp = (STATUS_ORDER[a.status] ?? 0) - (STATUS_ORDER[b.status] ?? 0);
          break;
        case 'createdAt':
          cmp = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [rawIncidents, sortField, sortDir]);

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(field === 'createdAt' ? 'desc' : 'asc');
    }
  }
  const total = data?.total ?? 0;
  const page = Math.floor((filters.skip ?? 0) / PAGE_SIZE);
  const totalPages = Math.ceil(total / PAGE_SIZE);

  function updateFilter(key: keyof IncidentFilters, value: string) {
    setFilters((f) => ({
      ...f,
      [key]: value || undefined,
      skip: 0,
    }));
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === incidents.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(incidents.map((i) => i.id)));
    }
  }

  const exportCsv = useCallback(() => {
    if (incidents.length === 0) return;
    const headers = ['ID', 'Title', 'Category', 'Severity', 'Status', 'Created', 'Resolved'];
    const rows = incidents.map((i) => [
      i.id,
      `"${i.title.replace(/"/g, '""')}"`,
      i.category,
      i.severity,
      i.status,
      new Date(i.createdAt).toISOString(),
      i.resolvedAt ? new Date(i.resolvedAt).toISOString() : '',
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `incidents-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [incidents]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Incidents</h1>
          <p className="text-sm text-muted-foreground">{total} total</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={exportCsv}
            disabled={incidents.length === 0}
            className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted disabled:opacity-50"
          >
            Export CSV
          </button>
        </div>

        {selected.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {selected.size} selected
            </span>
            <button
              onClick={() =>
                bulkMutation.mutate({
                  ids: Array.from(selected),
                  status: 'resolved',
                })
              }
              className="rounded-lg bg-green-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-500/100"
            >
              Resolve
            </button>
            <button
              onClick={() =>
                bulkMutation.mutate({
                  ids: Array.from(selected),
                  status: 'dismissed',
                })
              }
              className="rounded-lg bg-muted px-3 py-1.5 text-sm font-medium text-white hover:bg-muted/80"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search incidents..."
          value={filters.q ?? ''}
          onChange={(e) => updateFilter('q', e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <select
          value={filters.status ?? ''}
          onChange={(e) => updateFilter('status', e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
        <select
          value={filters.severity ?? ''}
          onChange={(e) => updateFilter('severity', e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="info">Info</option>
        </select>
        <select
          value={filters.category ?? ''}
          onChange={(e) => updateFilter('category', e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">All categories</option>
          <option value="hallucination">Hallucination</option>
          <option value="pii_leak">PII Leak</option>
          <option value="compliance">Compliance</option>
          <option value="cost_anomaly">Cost Anomaly</option>
          <option value="loop">Loop</option>
          <option value="prompt_injection">Prompt Injection</option>
          <option value="prompt_extraction">Prompt Extraction</option>
          <option value="toxicity">Toxicity & Bias</option>
          <option value="tool_call">Tool Call Validation</option>
          <option value="mcp_security">MCP Security</option>
        </select>
        <input
          type="date"
          value={filters.dateFrom ?? ''}
          onChange={(e) => updateFilter('dateFrom', e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm text-foreground"
          title="From date"
        />
        <input
          type="date"
          value={filters.dateTo ?? ''}
          onChange={(e) => updateFilter('dateTo', e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm text-foreground"
          title="To date"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card">
        {isError ? (
          <div className="py-4">
            <QueryError message="Failed to load incidents." onRetry={refetch} />
          </div>
        ) : isLoading ? (
          <TableSkeleton rows={8} cols={6} />
        ) : incidents.length === 0 ? (
          <div className="py-4">
            <EmptyState
              icon={ShieldAlert}
              title="No incidents found"
              description="No incidents match your current filters. Try adjusting your search criteria."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  <th className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selected.size === incidents.length && incidents.length > 0}
                      onChange={toggleAll}
                      className="rounded border-border"
                    />
                  </th>
                  <SortableHeader field="title" label="Title" current={sortField} dir={sortDir} onSort={toggleSort} />
                  <SortableHeader field="category" label="Category" current={sortField} dir={sortDir} onSort={toggleSort} />
                  <SortableHeader field="severity" label="Severity" current={sortField} dir={sortDir} onSort={toggleSort} />
                  <SortableHeader field="status" label="Status" current={sortField} dir={sortDir} onSort={toggleSort} />
                  <SortableHeader field="createdAt" label="Created" current={sortField} dir={sortDir} onSort={toggleSort} />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {incidents.map((inc) => (
                  <IncidentRow
                    key={inc.id}
                    incident={inc}
                    selected={selected.has(inc.id)}
                    onToggle={() => toggleSelect(inc.id)}
                  />
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <nav aria-label="Incidents pagination" className="flex items-center justify-between border-t border-border px-4 py-3">
                <button
                  disabled={page === 0}
                  aria-label="Go to previous page"
                  onClick={() =>
                    setFilters((f) => ({
                      ...f,
                      skip: Math.max(0, (f.skip ?? 0) - PAGE_SIZE),
                    }))
                  }
                  className="rounded-lg px-3 py-1.5 text-sm text-foreground hover:bg-muted disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-sm text-muted-foreground" aria-current="page">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  disabled={page >= totalPages - 1}
                  aria-label="Go to next page"
                  onClick={() =>
                    setFilters((f) => ({
                      ...f,
                      skip: (f.skip ?? 0) + PAGE_SIZE,
                    }))
                  }
                  className="rounded-lg px-3 py-1.5 text-sm text-foreground hover:bg-muted disabled:opacity-50"
                >
                  Next
                </button>
              </nav>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function IncidentRow({
  incident,
  selected,
  onToggle,
}: {
  incident: Incident;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <tr className={clsx('hover:bg-muted/50', selected && 'bg-primary/10')}>
      <td className="px-4 py-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          className="rounded border-border"
        />
      </td>
      <td className="px-4 py-3 text-sm font-medium text-foreground">
        <Link
          href={`/dashboard/incidents/${incident.id}`}
          className="hover:text-primary"
        >
          {incident.title}
        </Link>
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {incident.category.replace('_', ' ')}
      </td>
      <td className="px-4 py-3">
        <span
          className={clsx(
            'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
            SEVERITY_COLORS[incident.severity] ?? 'bg-muted text-muted-foreground',
          )}
        >
          {incident.severity}
        </span>
      </td>
      <td className="px-4 py-3">
        <span
          className={clsx(
            'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
            STATUS_COLORS[incident.status] ?? 'bg-muted text-muted-foreground',
          )}
        >
          {incident.status}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground" title={new Date(incident.createdAt).toLocaleString()}>
        {timeAgo(incident.createdAt)}
      </td>
    </tr>
  );
}

function SortableHeader({
  field,
  label,
  current,
  dir,
  onSort,
}: {
  field: SortField;
  label: string;
  current: SortField;
  dir: SortDir;
  onSort: (f: SortField) => void;
}) {
  const isActive = current === field;
  return (
    <th className="px-4 py-3" aria-sort={isActive ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
      <button
        onClick={() => onSort(field)}
        aria-label={`Sort by ${label}${isActive ? (dir === 'asc' ? ', ascending' : ', descending') : ''}`}
        className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
      >
        {label}
        {isActive ? (
          dir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-40" />
        )}
      </button>
    </th>
  );
}
