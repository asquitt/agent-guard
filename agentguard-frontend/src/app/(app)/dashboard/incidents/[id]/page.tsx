'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { getIncident, updateIncidentStatus, addIncidentAction } from '@/lib/api';
import type { IncidentAction } from '@/types';
import { SEVERITY_COLORS_BORDERED as SEVERITY_COLORS, STATUS_COLORS } from '@/lib/constants';

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = params.id as string;

  const { data: incident, isLoading } = useQuery({
    queryKey: ['incident', id],
    queryFn: () => getIncident(id),
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateIncidentStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
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
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="py-20 text-center text-gray-500">Incident not found</div>
    );
  }

  const canResolve = incident.status === 'open' || incident.status === 'acknowledged';
  const canAcknowledge = incident.status === 'open';

  return (
    <div>
      {/* Back link */}
      <button
        onClick={() => router.back()}
        className="mb-4 text-sm text-gray-500 hover:text-gray-700"
      >
        ← Back to incidents
      </button>

      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{incident.title}</h1>
          <div className="mt-2 flex items-center gap-3">
            <span
              className={clsx(
                'inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium',
                SEVERITY_COLORS[incident.severity] ?? 'bg-gray-100 text-gray-600',
              )}
            >
              {incident.severity}
            </span>
            <span
              className={clsx(
                'inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium',
                STATUS_COLORS[incident.status] ?? 'bg-gray-100 text-gray-600',
              )}
            >
              {incident.status}
            </span>
            <span className="text-sm text-gray-500">
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
              className="rounded-lg bg-warning-600 px-4 py-2 text-sm font-medium text-white hover:bg-warning-500 disabled:opacity-50"
            >
              Acknowledge
            </button>
          )}
          {canResolve && (
            <button
              onClick={() => statusMutation.mutate('resolved')}
              disabled={statusMutation.isPending}
              className="rounded-lg bg-success-600 px-4 py-2 text-sm font-medium text-white hover:bg-success-500 disabled:opacity-50"
            >
              Resolve
            </button>
          )}
          {canResolve && (
            <button
              onClick={() => statusMutation.mutate('dismissed')}
              disabled={statusMutation.isPending}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>

      {/* Metadata grid */}
      <div className="mb-6 grid grid-cols-2 gap-4 rounded-xl border border-gray-200 bg-white p-6 lg:grid-cols-4">
        <MetaItem label="Created" value={new Date(incident.createdAt).toLocaleString()} />
        <MetaItem
          label="Resolved"
          value={
            incident.resolvedAt
              ? new Date(incident.resolvedAt).toLocaleString()
              : '—'
          }
        />
        <MetaItem
          label="Action Taken"
          value={incident.actionTaken ?? 'None'}
        />
        <MetaItem
          label="Detector ID"
          value={incident.detectorId?.slice(0, 8) ?? '—'}
        />
      </div>

      {/* Description */}
      {incident.description && (
        <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-2 text-sm font-medium text-gray-900">
            Description
          </h2>
          <p className="whitespace-pre-wrap text-sm text-gray-600">
            {incident.description}
          </p>
        </div>
      )}

      {/* Action timeline */}
      <div className="rounded-xl border border-gray-200 bg-white">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
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
          <div className="py-8 text-center text-sm text-gray-500">
            No actions yet
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
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
      <p className="text-xs font-medium uppercase text-gray-500">{label}</p>
      <p className="mt-1 text-sm text-gray-900">{value}</p>
    </div>
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
        <span className="text-sm font-medium text-gray-900">
          {action.actionType.replace('_', ' ')}
        </span>
        <span className="text-xs text-gray-500">
          {new Date(action.createdAt).toLocaleString()}
        </span>
      </div>
      {note && <p className="mt-1 text-sm text-gray-600">{note}</p>}
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
        className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
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
        className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
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
        className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
      />
      <button
        onClick={handleSubmit}
        disabled={isPending}
        className="rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
      >
        Add
      </button>
      <button
        onClick={() => setOpen(false)}
        className="text-sm text-gray-500 hover:text-gray-700"
      >
        Cancel
      </button>
    </div>
  );
}
