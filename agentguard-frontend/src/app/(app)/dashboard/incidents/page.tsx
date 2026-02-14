'use client';

import { Suspense, useCallback, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { clsx } from 'clsx';
import { listIncidents, bulkUpdateStatus } from '@/lib/api';
import type { Incident, IncidentFilters } from '@/types';
import { useToast } from '@/hooks/useToast';
import { useListKeyNav } from '@/hooks/useListKeyNav';
import { useUrlFilters } from '@/hooks/useUrlFilters';
import { useTableDensity, DENSITY_CLASSES } from '@/hooks/useTableDensity';
import { useSavedViews } from '@/hooks/useSavedViews';
import { TableSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { QueryError } from '@/components/ui/QueryError';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { DensityToggle } from '@/components/ui/DensityToggle';
import { IncidentRow, IncidentCard } from '@/components/incidents/IncidentRow';
import { ActiveFilterChips } from '@/components/incidents/ActiveFilterChips';
import { ShieldAlert, ArrowUpDown, ArrowUp, ArrowDown, X, Download } from 'lucide-react';

type SortField = 'title' | 'category' | 'severity' | 'status' | 'createdAt';
type SortDir = 'asc' | 'desc';

const SEVERITY_ORDER: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };
const STATUS_ORDER: Record<string, number> = { open: 3, acknowledged: 2, resolved: 1, dismissed: 0 };

const PAGE_SIZE = 20;

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const TIME_QUICK_PICKS = [
  { label: '1h', ms: HOUR },
  { label: '24h', ms: DAY },
  { label: '7d', ms: 7 * DAY },
  { label: '30d', ms: 30 * DAY },
] as const;

export default function IncidentsPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={8} cols={6} />}>
      <IncidentsContent />
    </Suspense>
  );
}

function IncidentsContent() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const router = useRouter();
  const { filters, setFilter, setFilters, resetFilters } = useUrlFilters({
    defaults: { limit: PAGE_SIZE, skip: 0 },
    numericKeys: ['skip', 'limit'],
  }) as {
    filters: IncidentFilters;
    setFilter: (key: keyof IncidentFilters & string, value: string | number | undefined) => void;
    setFilters: (next: Partial<IncidentFilters>) => void;
    resetFilters: () => void;
  };
  const { isCompact } = useTableDensity();
  const dc = isCompact ? DENSITY_CLASSES.compact : DENSITY_CLASSES.comfortable;
  const { views: savedViews, save: saveView, remove: removeView } = useSavedViews('incidents');
  const [showSaveInput, setShowSaveInput] = useState(false);
  const [viewName, setViewName] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const sortField = (filters.sort as SortField) || 'createdAt';
  const sortDir = (filters.dir as SortDir) || 'desc';
  const [bulkAction, setBulkAction] = useState<'resolved' | 'dismissed' | null>(null);

  const hasActiveFilters = !!(filters.severity || filters.status || filters.category || filters.q);

  const { data, isLoading, isFetching, isError, refetch } = useQuery({
    queryKey: ['incidents', filters],
    queryFn: () => listIncidents(filters),
  });
  const isRefetching = isFetching && !isLoading;

  const bulkMutation = useMutation({
    mutationFn: ({ ids, status }: { ids: string[]; status: string }) =>
      bulkUpdateStatus(ids, status),
    onSuccess: (_data, { ids, status }) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      setSelected(new Set());
      toast.success(`${ids.length} incident${ids.length !== 1 ? 's' : ''} ${status}`);
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

  const handleListSelect = useCallback(
    (index: number) => {
      const inc = incidents[index];
      if (inc) router.push(`/dashboard/incidents/${inc.id}`);
    },
    [incidents, router],
  );
  const { focusedIndex } = useListKeyNav(incidents.length, handleListSelect);

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setFilter('dir', sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setFilters({ ...filters, sort: field, dir: field === 'createdAt' ? 'desc' : 'asc' });
    }
  }
  const total = data?.total ?? 0;
  const page = Math.floor((filters.skip ?? 0) / PAGE_SIZE);
  const totalPages = Math.ceil(total / PAGE_SIZE);

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
      {/* Bulk action confirm dialog */}
      <ConfirmDialog
        open={bulkAction !== null}
        title={bulkAction === 'resolved' ? 'Resolve Incidents' : 'Dismiss Incidents'}
        description={`${bulkAction === 'resolved' ? 'Resolve' : 'Dismiss'} ${selected.size} selected incident${selected.size !== 1 ? 's' : ''}?`}
        confirmLabel={bulkAction === 'resolved' ? 'Resolve' : 'Dismiss'}
        variant={bulkAction === 'dismissed' ? 'danger' : 'default'}
        loading={bulkMutation.isPending}
        onConfirm={() => {
          if (bulkAction) bulkMutation.mutate({ ids: Array.from(selected), status: bulkAction });
          setBulkAction(null);
        }}
        onCancel={() => setBulkAction(null)}
      />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Incidents</h1>
          <p className="text-sm text-muted-foreground">{total} total</p>
        </div>

        <div className="flex items-center gap-2">
          <DensityToggle />
          <button
            onClick={exportCsv}
            disabled={incidents.length === 0}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted disabled:opacity-50"
          >
            <Download className="h-3.5 w-3.5" />
            Export
          </button>
        </div>

        {selected.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {selected.size} selected
            </span>
            <button
              onClick={() => setBulkAction('resolved')}
              className="rounded-lg bg-green-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-500/100"
            >
              Resolve
            </button>
            <button
              onClick={() => setBulkAction('dismissed')}
              className="rounded-lg bg-muted px-3 py-1.5 text-sm font-medium text-white hover:bg-muted/80"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Saved views */}
      {(savedViews.length > 0 || showSaveInput) && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {savedViews.map((view) => (
            <span
              key={view.id}
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-muted/50 text-xs"
            >
              <button
                onClick={() => setFilters(view.filters as Partial<IncidentFilters>)}
                className="px-2.5 py-1 font-medium text-foreground hover:text-primary transition-colors"
              >
                {view.name}
              </button>
              <button
                onClick={() => removeView(view.id)}
                className="pr-1.5 text-muted-foreground/60 hover:text-red-500 transition-colors"
                aria-label={`Remove ${view.name} view`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          {showSaveInput ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (viewName.trim()) {
                  saveView(viewName.trim(), filters as Record<string, string | number | undefined>);
                  setViewName('');
                  setShowSaveInput(false);
                }
              }}
              className="inline-flex items-center gap-1"
            >
              <input
                autoFocus
                value={viewName}
                onChange={(e) => setViewName(e.target.value)}
                placeholder="View name..."
                className="w-32 rounded-md border border-border bg-background px-2 py-1 text-xs"
              />
              <button
                type="submit"
                disabled={!viewName.trim()}
                className="rounded-md bg-primary px-2 py-1 text-xs font-medium text-primary-foreground disabled:opacity-50"
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => { setShowSaveInput(false); setViewName(''); }}
                className="text-xs text-muted-foreground"
              >
                Cancel
              </button>
            </form>
          ) : (
            <button
              onClick={() => setShowSaveInput(true)}
              className="rounded-lg border border-dashed border-border px-2.5 py-1 text-xs text-muted-foreground hover:border-primary hover:text-primary transition-colors"
            >
              + Save current view
            </button>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search incidents..."
          value={filters.q ?? ''}
          onChange={(e) => setFilter('q', e.target.value || undefined)}
          className="rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <select
          value={filters.status ?? ''}
          onChange={(e) => setFilter('status', e.target.value || undefined)}
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
          onChange={(e) => setFilter('severity', e.target.value || undefined)}
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
          onChange={(e) => setFilter('category', e.target.value || undefined)}
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
        <div className="flex items-center gap-1 rounded-lg border border-border px-1">
          {TIME_QUICK_PICKS.map((tp) => (
            <button
              key={tp.label}
              onClick={() => {
                const from = new Date(Date.now() - tp.ms).toISOString().slice(0, 10);
                setFilters({ ...filters, dateFrom: from, dateTo: undefined });
              }}
              className={clsx(
                'rounded-md px-2 py-1.5 text-xs font-medium transition-colors',
                filters.dateFrom === new Date(Date.now() - tp.ms).toISOString().slice(0, 10) && !filters.dateTo
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {tp.label}
            </button>
          ))}
        </div>
        <input
          type="date"
          value={filters.dateFrom ?? ''}
          onChange={(e) => setFilter('dateFrom', e.target.value || undefined)}
          className="rounded-lg border border-border px-3 py-2 text-sm text-foreground"
          title="From date"
        />
        <input
          type="date"
          value={filters.dateTo ?? ''}
          onChange={(e) => setFilter('dateTo', e.target.value || undefined)}
          className="rounded-lg border border-border px-3 py-2 text-sm text-foreground"
          title="To date"
        />
      </div>

      {/* Active filter chips */}
      <ActiveFilterChips filters={filters} onClear={setFilter} onClearAll={resetFilters} />

      {/* Table */}
      <div className="relative rounded-xl border border-border bg-card">
        {/* Inline loading bar for filter/sort changes */}
        {isRefetching && (
          <div className="absolute inset-x-0 top-0 z-10 h-0.5 overflow-hidden rounded-t-xl">
            <div className="h-full w-1/3 animate-shimmer bg-primary" />
          </div>
        )}
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
              description={
                hasActiveFilters
                  ? 'No incidents match your current filters. Try adjusting your search criteria.'
                  : 'No incidents detected yet. Start proxying LLM traffic to monitor for threats.'
              }
              hints={
                hasActiveFilters
                  ? undefined
                  : [
                      { label: 'Configure detectors', href: '/dashboard/detectors' },
                      { label: 'Create an API key', href: '/dashboard/api-keys' },
                    ]
              }
              action={
                hasActiveFilters
                  ? { label: 'Clear filters', onClick: resetFilters }
                  : undefined
              }
            />
          </div>
        ) : (
          <>
            {/* Mobile card view */}
            <div className="space-y-3 md:hidden">
              {incidents.map((inc) => (
                <IncidentCard key={inc.id} incident={inc} />
              ))}
            </div>

            {/* Desktop table view */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full">
                <thead>
                  <tr className={clsx('border-b border-border text-left font-medium uppercase tracking-wider text-muted-foreground', dc.header)}>
                    <th className={dc.header}>
                      <input
                        type="checkbox"
                        checked={selected.size === incidents.length && incidents.length > 0}
                        onChange={toggleAll}
                        className="rounded border-border"
                      />
                    </th>
                    <SortableHeader field="title" label="Title" current={sortField} dir={sortDir} onSort={toggleSort} headerClass={dc.header} />
                    <SortableHeader field="category" label="Category" current={sortField} dir={sortDir} onSort={toggleSort} headerClass={dc.header} />
                    <SortableHeader field="severity" label="Severity" current={sortField} dir={sortDir} onSort={toggleSort} headerClass={dc.header} />
                    <SortableHeader field="status" label="Status" current={sortField} dir={sortDir} onSort={toggleSort} headerClass={dc.header} />
                    <SortableHeader field="createdAt" label="Created" current={sortField} dir={sortDir} onSort={toggleSort} headerClass={dc.header} />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {incidents.map((inc, i) => (
                    <IncidentRow
                      key={inc.id}
                      incident={inc}
                      cellClass={dc.cell}
                      selected={selected.has(inc.id)}
                      focused={i === focusedIndex}
                      onToggle={() => toggleSelect(inc.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <nav aria-label="Incidents pagination" className="flex items-center justify-between border-t border-border px-4 py-3">
                <button
                  disabled={page === 0}
                  aria-label="Go to previous page"
                  onClick={() =>
                    setFilter('skip', Math.max(0, (filters.skip ?? 0) - PAGE_SIZE))
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
                    setFilter('skip', (filters.skip ?? 0) + PAGE_SIZE)
                  }
                  className="rounded-lg px-3 py-1.5 text-sm text-foreground hover:bg-muted disabled:opacity-50"
                >
                  Next
                </button>
              </nav>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function SortableHeader({
  field,
  label,
  current,
  dir,
  onSort,
  headerClass,
}: {
  field: SortField;
  label: string;
  current: SortField;
  dir: SortDir;
  onSort: (f: SortField) => void;
  headerClass?: string;
}) {
  const isActive = current === field;
  return (
    <th className={headerClass ?? 'px-4 py-3'} aria-sort={isActive ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
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

