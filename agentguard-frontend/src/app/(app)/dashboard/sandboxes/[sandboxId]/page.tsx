'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  getSandbox,
  listExecutions,
  getSandboxAuditLogs,
  startExecution,
} from '@/lib/api/sandboxes';
import CapabilityManager from '@/components/sandboxes/CapabilityManager';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-zinc-500/10 text-zinc-400 ring-1 ring-inset ring-zinc-500/20',
  provisioning: 'bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20',
  running: 'bg-green-500/10 text-green-400 ring-1 ring-inset ring-green-500/20',
  paused: 'bg-yellow-500/10 text-yellow-400 ring-1 ring-inset ring-yellow-500/20',
  terminated: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
  failed: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
};

type Tab = 'overview' | 'capabilities' | 'executions' | 'audit';

export default function SandboxDetailPage() {
  const params = useParams();
  const sandboxId = params.sandboxId as string;
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const { data: sandbox, isLoading } = useQuery({
    queryKey: ['sandboxes', sandboxId],
    queryFn: () => getSandbox(sandboxId),
  });

  const { data: executions } = useQuery({
    queryKey: ['sandboxes', sandboxId, 'executions'],
    queryFn: () => listExecutions(sandboxId),
    enabled: activeTab === 'executions',
  });

  const { data: auditLogs } = useQuery({
    queryKey: ['sandboxes', sandboxId, 'audit'],
    queryFn: () => getSandboxAuditLogs(sandboxId),
    enabled: activeTab === 'audit',
  });

  const execMutation = useMutation({
    mutationFn: () => startExecution(sandboxId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sandboxes'] }),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!sandbox) {
    return <div className="text-center text-muted-foreground py-12">Sandbox not found</div>;
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'capabilities', label: `Capabilities (${sandbox.capabilities?.length ?? 0})` },
    { key: 'executions', label: 'Executions' },
    { key: 'audit', label: 'Audit Log' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Link href="/dashboard/sandboxes" className="text-sm text-muted-foreground hover:text-foreground">Sandboxes</Link>
            <span className="text-muted-foreground">/</span>
            <h1 className="text-2xl font-bold text-foreground">{sandbox.name}</h1>
          </div>
          {sandbox.description && <p className="mt-1 text-sm text-muted-foreground">{sandbox.description}</p>}
        </div>
        <div className="flex items-center gap-3">
          <span className={clsx('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium', STATUS_COLORS[sandbox.status] ?? STATUS_COLORS.pending)}>
            {sandbox.status}
          </span>
          {sandbox.status !== 'running' && (
            <button onClick={() => execMutation.mutate()} disabled={execMutation.isPending} className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
              {execMutation.isPending ? 'Starting...' : 'Start Execution'}
            </button>
          )}
        </div>
      </div>

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

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="mb-4 text-sm font-semibold text-foreground">Resource Limits</h3>
            <dl className="space-y-3">
              <div className="flex justify-between text-sm"><dt className="text-muted-foreground">CPU Shares</dt><dd className="text-foreground">{sandbox.resourceLimits?.cpu_shares ?? 512}</dd></div>
              <div className="flex justify-between text-sm"><dt className="text-muted-foreground">Memory</dt><dd className="text-foreground">{sandbox.resourceLimits?.memory_mb ?? 256} MB</dd></div>
              <div className="flex justify-between text-sm"><dt className="text-muted-foreground">Token Budget</dt><dd className="text-foreground">{(sandbox.resourceLimits?.max_tokens ?? 10000).toLocaleString()}</dd></div>
              <div className="flex justify-between text-sm"><dt className="text-muted-foreground">Timeout</dt><dd className="text-foreground">{sandbox.resourceLimits?.timeout_seconds ?? 300}s</dd></div>
            </dl>
          </div>
          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="mb-4 text-sm font-semibold text-foreground">Network Policy</h3>
            <dl className="space-y-3">
              <div className="flex justify-between text-sm">
                <dt className="text-muted-foreground">Egress</dt>
                <dd className={sandbox.networkPolicy?.deny_all_egress ? 'text-red-400' : 'text-green-400'}>
                  {sandbox.networkPolicy?.deny_all_egress ? 'Deny All (Whitelist Only)' : 'Allow All'}
                </dd>
              </div>
              <div className="text-sm">
                <dt className="text-muted-foreground mb-1">Allowed Hosts</dt>
                <dd className="space-y-1">
                  {sandbox.networkPolicy?.allowed_hosts?.length ? (
                    sandbox.networkPolicy.allowed_hosts.map((host: string) => (
                      <span key={host} className="mr-2 inline-flex rounded bg-muted px-2 py-0.5 text-xs text-foreground">{host}</span>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground">None (fully isolated)</span>
                  )}
                </dd>
              </div>
              <div className="text-sm">
                <dt className="text-muted-foreground mb-1">Allowed Ports</dt>
                <dd>{sandbox.networkPolicy?.allowed_ports?.join(', ') || '443, 80'}</dd>
              </div>
            </dl>
          </div>
          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="mb-4 text-sm font-semibold text-foreground">Configuration</h3>
            <dl className="space-y-3">
              <div className="flex justify-between text-sm"><dt className="text-muted-foreground">Image</dt><dd className="text-foreground font-mono text-xs">{sandbox.image}</dd></div>
              <div className="flex justify-between text-sm"><dt className="text-muted-foreground">Agent</dt><dd className="text-foreground">{sandbox.agentId ? <Link href="/dashboard/agents" className="text-primary hover:underline">{sandbox.agentId.slice(0, 8)}...</Link> : 'None'}</dd></div>
              <div className="flex justify-between text-sm"><dt className="text-muted-foreground">Created</dt><dd className="text-foreground">{new Date(sandbox.createdAt).toLocaleString()}</dd></div>
            </dl>
          </div>
          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="mb-4 text-sm font-semibold text-foreground">Environment Variables</h3>
            {Object.keys(sandbox.environment || {}).length > 0 ? (
              <dl className="space-y-2">
                {Object.entries(sandbox.environment).map(([key]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <dt className="font-mono text-xs text-muted-foreground">{key}</dt>
                    <dd className="text-foreground">••••••••</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-xs text-muted-foreground">No environment variables set</p>
            )}
          </div>
        </div>
      )}

      {/* Capabilities Tab */}
      {activeTab === 'capabilities' && (
        <CapabilityManager sandboxId={sandboxId} capabilities={sandbox.capabilities ?? []} />
      )}

      {/* Executions Tab */}
      {activeTab === 'executions' && (
        <div className="rounded-xl border border-border bg-card">
          {executions?.items?.length ? (
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Trigger</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Tokens</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Started</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {executions.items.map((exec) => {
                  const duration = exec.startedAt && exec.finishedAt
                    ? Math.round((new Date(exec.finishedAt).getTime() - new Date(exec.startedAt).getTime()) / 1000)
                    : null;
                  return (
                    <tr key={exec.id} className="hover:bg-muted/50">
                      <td className="px-4 py-3">
                        <Link href={`/dashboard/sandboxes/${sandboxId}/executions/${exec.id}`} className="font-mono text-xs text-primary hover:underline">
                          {exec.id.slice(0, 8)}...
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', STATUS_COLORS[exec.status] ?? STATUS_COLORS.pending)}>
                          {exec.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{exec.trigger}</td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{exec.resourceUsage?.tokens_used?.toLocaleString() ?? 0}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{exec.startedAt ? new Date(exec.startedAt).toLocaleString() : '-'}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{duration !== null ? `${duration}s` : '-'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-muted-foreground">No executions yet.</div>
          )}
        </div>
      )}

      {/* Audit Tab */}
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
