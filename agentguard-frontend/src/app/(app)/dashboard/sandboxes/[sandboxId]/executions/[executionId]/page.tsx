'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  getExecution,
  stopExecution,
  terminateExecution,
  getExecutionAuditLogs,
} from '@/lib/api/sandboxes';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-zinc-500/10 text-zinc-400 ring-1 ring-inset ring-zinc-500/20',
  provisioning: 'bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20',
  running: 'bg-green-500/10 text-green-400 ring-1 ring-inset ring-green-500/20',
  paused: 'bg-yellow-500/10 text-yellow-400 ring-1 ring-inset ring-yellow-500/20',
  terminated: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
  failed: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
};

type Tab = 'resources' | 'audit';

function ResourceGauge({ label, value, max, unit }: { label: string; value: number; max: number; unit: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-green-500';

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="text-foreground font-medium">
          {value.toLocaleString()} / {max.toLocaleString()} {unit}
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div className={clsx('h-2 rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function ExecutionDetailPage() {
  const params = useParams();
  const sandboxId = params.sandboxId as string;
  const executionId = params.executionId as string;
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>('resources');

  const { data: execution, isLoading } = useQuery({
    queryKey: ['executions', executionId],
    queryFn: () => getExecution(executionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' || status === 'provisioning' ? 3000 : false;
    },
  });

  const { data: auditLogs } = useQuery({
    queryKey: ['executions', executionId, 'audit'],
    queryFn: () => getExecutionAuditLogs(executionId),
    enabled: activeTab === 'audit',
    refetchInterval: execution?.status === 'running' ? 5000 : false,
  });

  const stopMut = useMutation({
    mutationFn: () => stopExecution(executionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['executions', executionId] }),
  });

  const terminateMut = useMutation({
    mutationFn: () => terminateExecution(executionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['executions', executionId] }),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!execution) {
    return <div className="text-center text-muted-foreground py-12">Execution not found</div>;
  }

  const duration =
    execution.startedAt && execution.finishedAt
      ? Math.round((new Date(execution.finishedAt).getTime() - new Date(execution.startedAt).getTime()) / 1000)
      : execution.startedAt
        ? Math.round((Date.now() - new Date(execution.startedAt).getTime()) / 1000)
        : null;

  const isActive = execution.status === 'running' || execution.status === 'provisioning';
  const usage = execution.resourceUsage;

  const tabs: { key: Tab; label: string }[] = [
    { key: 'resources', label: 'Resources' },
    { key: 'audit', label: `Audit Log (${auditLogs?.total ?? '...'})` },
  ];

  const allowed = auditLogs?.items?.filter((l) => l.allowed).length ?? 0;
  const denied = auditLogs?.items?.filter((l) => !l.allowed).length ?? 0;

  return (
    <div className="space-y-6">
      {/* Breadcrumb + Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Link href="/dashboard/sandboxes" className="hover:text-foreground">Sandboxes</Link>
            <span>/</span>
            <Link href={`/dashboard/sandboxes/${sandboxId}`} className="hover:text-foreground">{sandboxId.slice(0, 8)}...</Link>
            <span>/</span>
            <span className="text-foreground font-medium">Execution {executionId.slice(0, 8)}...</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={clsx('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium', STATUS_COLORS[execution.status] ?? STATUS_COLORS.pending)}>
            {execution.status}
          </span>
          {isActive && (
            <>
              <button onClick={() => stopMut.mutate()} disabled={stopMut.isPending} className="rounded-lg bg-yellow-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-yellow-700 disabled:opacity-50">
                {stopMut.isPending ? 'Stopping...' : 'Stop'}
              </button>
              <button onClick={() => terminateMut.mutate()} disabled={terminateMut.isPending} className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">
                {terminateMut.isPending ? 'Terminating...' : 'Terminate'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Trigger</p>
          <p className="mt-1 text-lg font-semibold text-foreground capitalize">{execution.trigger}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Duration</p>
          <p className="mt-1 text-lg font-semibold text-foreground">{duration !== null ? `${duration}s` : '-'}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Exit Code</p>
          <p className={clsx('mt-1 text-lg font-semibold', execution.exitCode === 0 ? 'text-green-400' : execution.exitCode !== null ? 'text-red-400' : 'text-muted-foreground')}>
            {execution.exitCode ?? '-'}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Container</p>
          <p className="mt-1 text-sm font-mono text-foreground truncate">{execution.containerId ?? '-'}</p>
        </div>
      </div>

      {/* Error Message */}
      {execution.errorMessage && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-4">
          <p className="text-sm font-medium text-red-400">Error</p>
          <p className="mt-1 text-sm text-red-300">{execution.errorMessage}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={clsx(
              'px-4 py-2 text-sm font-medium -mb-px',
              activeTab === tab.key
                ? 'border-b-2 border-primary text-primary'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Resources Tab */}
      {activeTab === 'resources' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-border bg-card p-6 space-y-5">
            <h3 className="text-sm font-semibold text-foreground">Resource Usage</h3>
            <ResourceGauge label="Memory" value={usage.memory_peak_mb} max={256} unit="MB" />
            <ResourceGauge label="Tokens" value={usage.tokens_used} max={10000} unit="" />
            <ResourceGauge label="CPU" value={usage.cpu_seconds} max={300} unit="s" />
          </div>
          <div className="rounded-xl border border-border bg-card p-6 space-y-5">
            <h3 className="text-sm font-semibold text-foreground">Network & Timing</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Network I/O</span>
                <span className="text-foreground">{(usage.network_bytes / 1024).toFixed(1)} KB</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Started</span>
                <span className="text-foreground">{execution.startedAt ? new Date(execution.startedAt).toLocaleString() : '-'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Finished</span>
                <span className="text-foreground">{execution.finishedAt ? new Date(execution.finishedAt).toLocaleString() : '-'}</span>
              </div>
            </div>
            {activeTab === 'resources' && auditLogs && (
              <div className="pt-3 border-t border-border">
                <h4 className="text-sm font-semibold text-foreground mb-3">Capability Decisions</h4>
                <div className="flex gap-4">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-green-500/10 text-xs text-green-400">&#10003;</span>
                    <span className="text-sm text-muted-foreground">{allowed} allowed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-red-500/10 text-xs text-red-400">&#10007;</span>
                    <span className="text-sm text-muted-foreground">{denied} denied</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Audit Log Tab */}
      {activeTab === 'audit' && (
        <div className="rounded-xl border border-border bg-card">
          {auditLogs?.items?.length ? (
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Time</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Action</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Result</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Capability</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {auditLogs.items.map((log) => (
                  <tr key={log.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3 text-xs text-muted-foreground">{new Date(log.timestamp).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-muted px-2 py-0.5 text-xs text-foreground">{log.actionType}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', log.allowed ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400')}>
                        {log.allowed ? 'Allowed' : 'Denied'}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{log.capabilityMatched || '-'}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground max-w-xs truncate">{JSON.stringify(log.actionDetail)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-muted-foreground">No audit log entries yet.</div>
          )}
        </div>
      )}
    </div>
  );
}
