'use client';

import { Suspense, useCallback, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { clsx } from 'clsx';
import { listIncidents, bulkUpdateStatus, updateIncidentStatus } from '@/lib/api';
import type { Incident, IncidentFilters } from '@/types';
import { SEVERITY_COLORS, STATUS_COLORS } from '@/lib/constants';
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
import { ShieldAlert, ArrowUpDown, ArrowUp, ArrowDown, X } from 'lucide-react';
import { timeAgo } from '@/lib/format';

type SortField = 'title' | 'category' | 'severity' | 'status' | 'createdAt';
type SortDir = 'asc' | 'desc';

const SEVERITY_ORDER: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };
const STATUS_ORDER: Record<string, number> = { open: 3, acknowledged: 2, resolved: 1, dismissed: 0 };

const PAGE_SIZE = 20;

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

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['incidents', filters],
    queryFn: () => listIncidents(filters),
  });

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
          </div>
        )}
      </div>
    </div>
  );
}

const INCIDENT_STATUSES = ['open', 'acknowledged', 'resolved', 'dismissed'] as const;

function IncidentRow({
  incident,
  cellClass,
  selected,
  focused,
  onToggle,
}: {
  incident: Incident;
  cellClass: string;
  selected: boolean;
  focused: boolean;
  onToggle: () => void;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateIncidentStatus(incident.id, status),
    onSuccess: (_data, status) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      toast.success(`Incident ${status}`);
    },
  });

  return (
    <tr className={clsx('hover:bg-muted/50', selected && 'bg-primary/10', focused && 'ring-2 ring-inset ring-primary/50 bg-primary/5')}>
      <td className={cellClass}>
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          className="rounded border-border"
        />
      </td>
      <td className={clsx(cellClass, 'font-medium text-foreground')}>
        <Link
          href={`/dashboard/incidents/${incident.id}`}
          className="hover:text-primary"
        >
          {incident.title}
        </Link>
      </td>
      <td className={clsx(cellClass, 'text-muted-foreground')}>
        {incident.category.replace('_', ' ')}
      </td>
      <td className={cellClass}>
        <span
          className={clsx(
            'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
            SEVERITY_COLORS[incident.severity] ?? 'bg-muted text-muted-foreground',
          )}
        >
          {incident.severity}
        </span>
      </td>
      <td className={cellClass}>
        <select
          value={incident.status}
          onChange={(e) => statusMutation.mutate(e.target.value)}
          disabled={statusMutation.isPending}
          className={clsx(
            'cursor-pointer rounded-full border-0 py-0.5 pl-2 pr-6 text-xs font-medium appearance-none bg-no-repeat',
            STATUS_COLORS[incident.status] ?? 'bg-muted text-muted-foreground',
            statusMutation.isPending && 'opacity-50',
          )}
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`,
            backgroundPosition: 'right 4px center',
          }}
        >
          {INCIDENT_STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </td>
      <td className={clsx(cellClass, 'text-muted-foreground')} title={new Date(incident.createdAt).toLocaleString()}>
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

const FILTER_LABELS: Record<string, string> = {
  status: 'Status',
  severity: 'Severity',
  category: 'Category',
  q: 'Search',
  dateFrom: 'From',
  dateTo: 'To',
  detectorId: 'Detector',
};

// Keys that are user-facing filters (exclude pagination, sort, internal keys)
const CHIP_KEYS = ['status', 'severity', 'category', 'q', 'dateFrom', 'dateTo', 'detectorId'];

function ActiveFilterChips({
  filters,
  onClear,
  onClearAll,
}: {
  filters: IncidentFilters;
  onClear: (key: keyof IncidentFilters & string, value: undefined) => void;
  onClearAll: () => void;
}) {
  const chips = CHIP_KEYS
    .filter((key) => {
      const val = filters[key as keyof IncidentFilters];
      return val !== undefined && val !== '';
    })
    .map((key) => ({
      key,
      label: FILTER_LABELS[key] ?? key,
      value: String(filters[key as keyof IncidentFilters]),
    }));

  if (chips.length === 0) return null;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      {chips.map((chip) => (
        <span
          key={chip.key}
          className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
        >
          {chip.label}: {chip.value}
          <button
            onClick={() => onClear(chip.key as keyof IncidentFilters & string, undefined)}
            className="ml-0.5 rounded-full p-0.5 hover:bg-primary/20 transition-colors"
            aria-label={`Remove ${chip.label} filter`}
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      {chips.length > 1 && (
        <button
          onClick={onClearAll}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
