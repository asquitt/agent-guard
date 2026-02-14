'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  deleteSandbox,
  getSandboxStats,
  listSandboxes,
  startExecution,
} from '@/lib/api/sandboxes';
import CreateSandboxForm from '@/components/sandboxes/CreateSandboxForm';
import type { SandboxData, SandboxFilters } from '@/types/sandbox';
import { QueryError } from '@/components/ui/QueryError';

const SANDBOX_STATUS_COLORS: Record<string, string> = {
  pending: 'bg-zinc-500/10 text-zinc-400 ring-1 ring-inset ring-zinc-500/20',
  provisioning: 'bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20',
  running: 'bg-green-500/10 text-green-400 ring-1 ring-inset ring-green-500/20',
  paused: 'bg-yellow-500/10 text-yellow-400 ring-1 ring-inset ring-yellow-500/20',
  terminated: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
  failed: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
};

const PAGE_SIZE = 20;

export default function SandboxesPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<SandboxFilters>({ limit: PAGE_SIZE });
  const [showCreate, setShowCreate] = useState(false);

  const { data: stats } = useQuery({
    queryKey: ['sandboxes', 'stats'],
    queryFn: getSandboxStats,
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['sandboxes', filters],
    queryFn: () => listSandboxes(filters),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSandbox,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sandboxes'] }),
  });

  const execMutation = useMutation({
    mutationFn: (sandboxId: string) => startExecution(sandboxId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sandboxes'] }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const page = Math.floor((filters.skip ?? 0) / PAGE_SIZE);
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Sandboxes</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Capability-based execution environments for agent containment
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90"
        >
          {showCreate ? 'Cancel' : 'Create Sandbox'}
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <StatCard label="Total" value={stats.totalSandboxes} />
          <StatCard label="Active" value={stats.activeSandboxes} color="text-green-400" />
          <StatCard label="Executions" value={stats.totalExecutions} />
          <StatCard label="Running" value={stats.runningExecutions} color="text-blue-400" />
          <StatCard label="Denied" value={stats.deniedActions} color="text-red-400" />
          <StatCard label="Tokens Used" value={stats.totalTokensUsed.toLocaleString()} />
        </div>
      )}

      {showCreate && (
        <CreateSandboxForm
          onClose={() => setShowCreate(false)}
          onSuccess={() => {
            setShowCreate(false);
            queryClient.invalidateQueries({ queryKey: ['sandboxes'] });
          }}
        />
      )}

      {/* Filters */}
      <div className="flex gap-2">
        {['', 'pending', 'running', 'terminated', 'failed'].map((s) => (
          <button
            key={s}
            onClick={() => setFilters((f) => ({ ...f, status: s || undefined, skip: 0 }))}
            className={clsx(
              'rounded-lg px-3 py-1.5 text-xs font-medium',
              (filters.status ?? '') === s
                ? 'bg-primary text-white'
                : 'bg-muted text-muted-foreground hover:bg-muted/80',
            )}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {/* Table */}
      {isError ? (
        <QueryError message="Failed to load sandboxes." onRetry={refetch} />
      ) : isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-12 text-center text-muted-foreground">
          No sandboxes found. Create one to get started.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Capabilities</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Resources</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Network</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((sandbox) => (
                <SandboxRow
                  key={sandbox.id}
                  sandbox={sandbox}
                  onStart={() => execMutation.mutate(sandbox.id)}
                  onDelete={() => deleteMutation.mutate(sandbox.id)}
                />
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border px-4 py-3">
              <span className="text-xs text-muted-foreground">
                {total} sandbox{total !== 1 ? 'es' : ''}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page === 0}
                  onClick={() => setFilters((f) => ({ ...f, skip: Math.max(0, (f.skip ?? 0) - PAGE_SIZE) }))}
                  className="rounded px-3 py-1 text-xs text-muted-foreground hover:bg-muted disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  disabled={page >= totalPages - 1}
                  onClick={() => setFilters((f) => ({ ...f, skip: (f.skip ?? 0) + PAGE_SIZE }))}
                  className="rounded px-3 py-1 text-xs text-muted-foreground hover:bg-muted disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={clsx('mt-1 text-2xl font-bold', color ?? 'text-foreground')}>{value}</p>
    </div>
  );
}

function SandboxRow({
  sandbox,
  onStart,
  onDelete,
}: {
  sandbox: SandboxData;
  onStart: () => void;
  onDelete: () => void;
}) {
  const caps = sandbox.capabilities?.length ?? 0;
  const network = sandbox.networkPolicy;
  const limits = sandbox.resourceLimits;

  return (
    <tr className="hover:bg-muted/50">
      <td className="px-4 py-3">
        <Link href={`/dashboard/sandboxes/${sandbox.id}`} className="font-medium text-foreground hover:text-primary">
          {sandbox.name}
        </Link>
        {sandbox.description && (
          <p className="mt-0.5 text-xs text-muted-foreground">{sandbox.description}</p>
        )}
      </td>
      <td className="px-4 py-3">
        <span className={clsx('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', SANDBOX_STATUS_COLORS[sandbox.status] ?? SANDBOX_STATUS_COLORS.pending)}>
          {sandbox.status}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">{caps} grant{caps !== 1 ? 's' : ''}</td>
      <td className="px-4 py-3 text-xs text-muted-foreground">
        {limits?.memory_mb ?? 256}MB / {(limits?.max_tokens ?? 10000).toLocaleString()} tokens
      </td>
      <td className="px-4 py-3 text-xs text-muted-foreground">
        {network?.deny_all_egress ? 'Restricted' : 'Open'}{' '}
        {network?.allowed_hosts?.length ? `(${network.allowed_hosts.length} hosts)` : ''}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-2">
          {sandbox.status !== 'running' && (
            <button onClick={onStart} className="rounded px-2 py-1 text-xs text-green-400 hover:bg-green-500/10">
              Start
            </button>
          )}
          <button onClick={onDelete} className="rounded px-2 py-1 text-xs text-red-400 hover:bg-red-500/10">
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}
