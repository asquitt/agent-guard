'use client';

import Link from 'next/link';
import { clsx } from 'clsx';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateIncidentStatus } from '@/lib/api';
import type { Incident } from '@/types';
import { SEVERITY_COLORS, STATUS_COLORS } from '@/lib/constants';
import { useToast } from '@/hooks/useToast';
import { timeAgo } from '@/lib/format';

const INCIDENT_STATUSES = ['open', 'acknowledged', 'resolved', 'dismissed'] as const;

export function IncidentRow({
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

/** Compact card for mobile screens — replaces the table row. */
export function IncidentCard({ incident }: { incident: Incident }) {
  return (
    <Link
      href={`/dashboard/incidents/${incident.id}`}
      className="block rounded-xl border border-border bg-card p-4 transition-colors hover:bg-muted/30"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-foreground line-clamp-1">
          {incident.title}
        </p>
        <span
          className={clsx(
            'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium',
            SEVERITY_COLORS[incident.severity] ?? 'bg-muted text-muted-foreground',
          )}
        >
          {incident.severity}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>{incident.category.replace('_', ' ')}</span>
        <span>·</span>
        <span
          className={clsx(
            'rounded-full px-1.5 py-0.5 text-[10px] font-medium',
            STATUS_COLORS[incident.status] ?? 'bg-muted text-muted-foreground',
          )}
        >
          {incident.status}
        </span>
        <span>·</span>
        <span>{timeAgo(incident.createdAt)}</span>
      </div>
    </Link>
  );
}
