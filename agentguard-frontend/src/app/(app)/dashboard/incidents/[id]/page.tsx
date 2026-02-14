'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { getIncident, updateIncidentStatus, addIncidentAction } from '@/lib/api';
import { getExecution } from '@/lib/api/sandboxes';
import type { IncidentAction } from '@/types';
import { useToast } from '@/hooks/useToast';
import { SEVERITY_COLORS_BORDERED as SEVERITY_COLORS, STATUS_COLORS } from '@/lib/constants';
import { DetectionTimeline } from '@/components/incidents/DetectionTimeline';
import { ResponsePlaybook } from '@/components/incidents/ResponsePlaybook';
import { QueryError } from '@/components/ui/QueryError';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = params.id as string;

  const toast = useToast();

  const { data: incident, isLoading, isError, refetch } = useQuery({
    queryKey: ['incident', id],
    queryFn: () => getIncident(id),
  });

  const { data: sandboxExecution } = useQuery({
    queryKey: ['sandbox-execution', incident?.sandboxExecutionId],
    queryFn: () => getExecution(incident!.sandboxExecutionId!),
    enabled: !!incident?.sandboxExecutionId,
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateIncidentStatus(id, status),
    onSuccess: (_data, status) => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      toast.success(`Incident ${status}`);
    },
  });

  const actionMutation = useMutation({
    mutationFn: ({
      actionType,
      details,
    }: {
      actionType: string;
      details?: Record<string, unknown>;
    }) => addIncidentAction(id, actionType, details),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] });
      toast.success('Action added');
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return <QueryError message="Failed to load incident details." onRetry={refetch} />;
  }

  if (!incident) {
    return (
      <div className="py-20 text-center text-muted-foreground">Incident not found</div>
    );
  }

  const canResolve = incident.status === 'open' || incident.status === 'acknowledged';
  const canAcknowledge = incident.status === 'open';
  const [pendingAction, setPendingAction] = useState<'resolved' | 'dismissed' | null>(null);
  const [quickStatusOpen, setQuickStatusOpen] = useState(false);

  const handleQuickStatus = useCallback(() => {
    if (incident) setQuickStatusOpen(true);
  }, [incident]);

  useEffect(() => {
    window.addEventListener('keyboard:quick-status', handleQuickStatus);
    return () => window.removeEventListener('keyboard:quick-status', handleQuickStatus);
  }, [handleQuickStatus]);

  return (
    <div>
      {/* Confirm dialog for resolve/dismiss */}
      <ConfirmDialog
        open={pendingAction !== null}
        title={pendingAction === 'resolved' ? 'Resolve Incident' : 'Dismiss Incident'}
        description={
          pendingAction === 'resolved'
            ? 'Mark this incident as resolved? This indicates the issue has been addressed.'
            : 'Dismiss this incident? This marks it as a false positive or non-actionable.'
        }
        confirmLabel={pendingAction === 'resolved' ? 'Resolve' : 'Dismiss'}
        variant={pendingAction === 'dismissed' ? 'danger' : 'default'}
        loading={statusMutation.isPending}
        onConfirm={() => {
          if (pendingAction) statusMutation.mutate(pendingAction);
          setPendingAction(null);
        }}
        onCancel={() => setPendingAction(null)}
      />

      {/* Quick status picker (E key) */}
      <QuickStatusPicker
        open={quickStatusOpen}
        currentStatus={incident.status}
        loading={statusMutation.isPending}
        onSelect={(s) => {
          statusMutation.mutate(s);
          setQuickStatusOpen(false);
        }}
        onClose={() => setQuickStatusOpen(false)}
      />

      {/* Back link */}
      <button
        onClick={() => router.back()}
        className="mb-4 text-sm text-muted-foreground hover:text-foreground"
      >
        ← Back to incidents
      </button>

      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-foreground">{incident.title}</h1>
            <CopyIdButton value={incident.id} />
          </div>
          <div className="mt-2 flex items-center gap-3">
            <span
              className={clsx(
                'inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium',
                SEVERITY_COLORS[incident.severity] ?? 'bg-muted text-muted-foreground',
              )}
            >
              {incident.severity}
            </span>
            <span
              className={clsx(
                'inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium',
                STATUS_COLORS[incident.status] ?? 'bg-muted text-muted-foreground',
              )}
            >
              {incident.status}
            </span>
            <span className="text-sm text-muted-foreground">
              {incident.category.replace('_', ' ')}
            </span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          {canAcknowledge && (
            <button
              onClick={() => statusMutation.mutate('acknowledged')}
              disabled={statusMutation.isPending}
              className="rounded-lg bg-yellow-500 px-4 py-2 text-sm font-medium text-white hover:bg-yellow-400 disabled:opacity-50"
            >
              Acknowledge
            </button>
          )}
          {canResolve && (
            <button
              onClick={() => setPendingAction('resolved')}
              disabled={statusMutation.isPending}
              className="rounded-lg bg-green-500 px-4 py-2 text-sm font-medium text-white hover:bg-green-500/100 disabled:opacity-50"
            >
              Resolve
            </button>
          )}
          {canResolve && (
            <button
              onClick={() => setPendingAction('dismissed')}
              disabled={statusMutation.isPending}
              className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50 disabled:opacity-50"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>

      {/* Metadata grid */}
      <div className="mb-6 grid grid-cols-2 gap-4 rounded-xl border border-border bg-card p-6 lg:grid-cols-4">
        <MetaItem label="Created" value={new Date(incident.createdAt).toLocaleString()} />
        <MetaItem label="Resolved" value={incident.resolvedAt ? new Date(incident.resolvedAt).toLocaleString() : '—'} />
        <MetaItem label="Action Taken" value={incident.actionTaken ?? 'None'} />
        <MetaItem label="Detector ID" value={incident.detectorId?.slice(0, 8) ?? '—'} />
      </div>

      {/* Sandbox context */}
      {incident.sandboxExecutionId && (
        <div className="mb-6 rounded-xl border border-orange-500/30 bg-orange-500/5 p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-foreground">Sandbox Context</h2>
            {sandboxExecution && (
              <Link href={`/dashboard/sandboxes/${sandboxExecution.sandboxId}/executions/${sandboxExecution.id}`} className="text-sm font-medium text-primary hover:underline">View execution →</Link>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetaItem label="Execution" value={incident.sandboxExecutionId.slice(0, 8)} />
            <MetaItem label="Status" value={sandboxExecution?.status ?? '—'} />
            <MetaItem label="Trigger" value={sandboxExecution?.trigger ?? '—'} />
            <MetaItem label="Container" value={sandboxExecution?.containerId?.slice(0, 12) ?? '—'} />
          </div>
        </div>
      )}

      {/* Detection Timeline */}
      <div className="mb-6">
        <DetectionTimeline incident={incident} />
      </div>

      {/* Description */}
      {incident.description && (
        <div className="mb-6 rounded-xl border border-border bg-card p-6">
          <h2 className="mb-2 text-sm font-medium text-foreground">
            Description
          </h2>
          <p className="whitespace-pre-wrap text-sm text-muted-foreground">
            {incident.description}
          </p>
        </div>
      )}

      {/* Response Playbook */}
      {(incident.status === 'open' || incident.status === 'acknowledged') && (
        <div className="mb-6">
          <ResponsePlaybook category={incident.category} />
        </div>
      )}

      {/* Action timeline */}
      <div className="rounded-xl border border-border bg-card">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-foreground">
            Activity ({incident.actions.length})
          </h2>
          <AddActionButton
            onAdd={(actionType, note) =>
              actionMutation.mutate({
                actionType,
                details: note ? { note } : undefined,
              })
            }
            isPending={actionMutation.isPending}
          />
        </div>

        {incident.actions.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            No actions yet
          </div>
        ) : (
          <div className="divide-y divide-border">
            {incident.actions.map((action) => (
              <ActionRow key={action.id} action={action} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm text-foreground">{value}</p>
    </div>
  );
}

function CopyIdButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <button
      onClick={handleCopy}
      title="Copy incident ID"
      className="rounded-md border border-border px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
    >
      {copied ? '✓ copied' : value.slice(0, 8)}
    </button>
  );
}

function ActionRow({ action }: { action: IncidentAction }) {
  const note =
    action.details && typeof action.details.note === 'string'
      ? action.details.note
      : null;

  return (
    <div className="px-6 py-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">
          {action.actionType.replace('_', ' ')}
        </span>
        <span className="text-xs text-muted-foreground">
          {new Date(action.createdAt).toLocaleString()}
        </span>
      </div>
      {note && <p className="mt-1 text-sm text-muted-foreground">{note}</p>}
    </div>
  );
}

function AddActionButton({
  onAdd,
  isPending,
}: {
  onAdd: (actionType: string, note: string) => void;
  isPending: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [actionType, setActionType] = useState('investigate');
  const [note, setNote] = useState('');

  function handleSubmit() {
    onAdd(actionType, note);
    setOpen(false);
    setNote('');
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted/50"
      >
        Add action
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={actionType}
        onChange={(e) => setActionType(e.target.value)}
        className="rounded-lg border border-border px-2 py-1.5 text-sm"
      >
        <option value="investigate">Investigate</option>
        <option value="escalate">Escalate</option>
        <option value="comment">Comment</option>
      </select>
      <input
        type="text"
        placeholder="Note..."
        value={note}
        onChange={(e) => setNote(e.target.value)}
        className="rounded-lg border border-border px-2 py-1.5 text-sm"
      />
      <button
        onClick={handleSubmit}
        disabled={isPending}
        className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary/80 disabled:opacity-50"
      >
        Add
      </button>
      <button
        onClick={() => setOpen(false)}
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        Cancel
      </button>
    </div>
  );
}

const STATUSES = [
  { value: 'open', label: 'Open', key: '1' },
  { value: 'acknowledged', label: 'Acknowledged', key: '2' },
  { value: 'resolved', label: 'Resolved', key: '3' },
  { value: 'dismissed', label: 'Dismissed', key: '4' },
] as const;

function QuickStatusPicker({
  open,
  currentStatus,
  loading,
  onSelect,
  onClose,
}: {
  open: boolean;
  currentStatus: string;
  loading: boolean;
  onSelect: (status: string) => void;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') { onClose(); return; }
      const match = STATUSES.find((s) => s.key === e.key);
      if (match && match.value !== currentStatus) {
        e.preventDefault();
        onSelect(match.value);
      }
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, currentStatus, onSelect, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="w-full max-w-xs rounded-xl border border-border bg-popover p-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="mb-3 text-xs font-semibold uppercase text-muted-foreground">
          Set Status
        </p>
        <div className="space-y-1">
          {STATUSES.map((s) => (
            <button
              key={s.value}
              onClick={() => s.value !== currentStatus && onSelect(s.value)}
              disabled={loading || s.value === currentStatus}
              className={clsx(
                'flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors',
                s.value === currentStatus
                  ? 'bg-primary/10 text-primary font-medium cursor-default'
                  : 'text-foreground hover:bg-muted',
              )}
            >
              <span className="flex items-center gap-2">
                <span
                  className={clsx(
                    'inline-block h-2 w-2 rounded-full',
                    STATUS_COLORS[s.value]?.includes('red') ? 'bg-red-400' :
                    STATUS_COLORS[s.value]?.includes('yellow') ? 'bg-yellow-400' :
                    STATUS_COLORS[s.value]?.includes('green') ? 'bg-green-400' :
                    'bg-zinc-400',
                  )}
                />
                {s.label}
              </span>
              <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                {s.key}
              </kbd>
            </button>
          ))}
        </div>
        <p className="mt-3 text-center text-[10px] text-muted-foreground">
          Press 1–4 or click · Esc to close
        </p>
      </div>
    </div>
  );
}
