'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { listAgents, createAgent, updateAgent, deleteAgent } from '@/lib/api';
import type { AgentData } from '@/lib/api';

const RISK_TIERS = ['low', 'medium', 'high', 'critical'] as const;
const STATUSES = ['draft', 'testing', 'production', 'deprecated'] as const;

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-muted text-muted-foreground',
  testing: 'bg-blue-100 text-blue-700',
  production: 'bg-green-100 text-green-700',
  deprecated: 'bg-red-100 text-red-600',
};

const FRAMEWORKS = ['SOX', 'PCI-DSS', 'FFIEC', 'NYDFS-500', 'DORA', 'EU-AI-Act'] as const;

export default function AgentsPage() {
  const queryClient = useQueryClient();
  const [filterStatus, setFilterStatus] = useState('');
  const [filterRisk, setFilterRisk] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['agents', filterStatus, filterRisk],
    queryFn: () =>
      listAgents({
        status: filterStatus || undefined,
        riskTier: filterRisk || undefined,
        limit: 100,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAgent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  });

  const agents = data?.items ?? [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Agent Registry</h1>
          <p className="text-sm text-muted-foreground">Register and govern your AI agents</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/100"
        >
          Register Agent
        </button>
      </div>

      {showCreate && (
        <CreateAgentForm
          onClose={() => setShowCreate(false)}
          onSuccess={() => {
            setShowCreate(false);
            queryClient.invalidateQueries({ queryKey: ['agents'] });
          }}
        />
      )}

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
        <select
          value={filterRisk}
          onChange={(e) => setFilterRisk(e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">All risk tiers</option>
          {RISK_TIERS.map((r) => (
            <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
          ))}
        </select>
      </div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total Agents" value={data?.total ?? 0} />
        <StatCard
          label="Production"
          value={agents.filter((a) => a.status === 'production').length}
          color="text-green-600"
        />
        <StatCard
          label="High/Critical Risk"
          value={agents.filter((a) => a.riskTier === 'high' || a.riskTier === 'critical').length}
          color="text-red-600"
        />
        <StatCard
          label="Testing"
          value={agents.filter((a) => a.status === 'testing').length}
          color="text-blue-600"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : agents.length === 0 ? (
          <div className="py-16 text-center text-sm text-muted-foreground">
            No agents registered yet. Click &ldquo;Register Agent&rdquo; to get started.
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Risk Tier</th>
                <th className="px-4 py-3">Provider / Model</th>
                <th className="px-4 py-3">Frameworks</th>
                <th className="px-4 py-3">Owner</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {agents.map((agent) => (
                <AgentRow
                  key={agent.id}
                  agent={agent}
                  onDelete={() => deleteMutation.mutate(agent.id)}
                  onRefresh={() => queryClient.invalidateQueries({ queryKey: ['agents'] })}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className={clsx('text-2xl font-bold', color ?? 'text-foreground')}>{value}</p>
    </div>
  );
}

function AgentRow({
  agent,
  onDelete,
  onRefresh,
}: {
  agent: AgentData;
  onDelete: () => void;
  onRefresh: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editStatus, setEditStatus] = useState(agent.status);

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => updateAgent(agent.id, data),
    onSuccess: () => {
      setEditing(false);
      onRefresh();
    },
  });

  return (
    <tr className="hover:bg-muted/50">
      <td className="px-4 py-3">
        <div className="text-sm font-medium text-foreground">{agent.name}</div>
        {agent.description && (
          <div className="text-xs text-muted-foreground truncate max-w-xs">{agent.description}</div>
        )}
      </td>
      <td className="px-4 py-3">
        {editing ? (
          <div className="flex gap-1">
            <select
              value={editStatus}
              onChange={(e) => setEditStatus(e.target.value)}
              className="rounded border border-border px-2 py-1 text-xs"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <button
              onClick={() => updateMutation.mutate({ status: editStatus })}
              className="text-xs text-primary hover:text-primary"
            >
              Save
            </button>
            <button onClick={() => setEditing(false)} className="text-xs text-muted-foreground/60">
              Cancel
            </button>
          </div>
        ) : (
          <span
            onClick={() => setEditing(true)}
            className={clsx(
              'inline-flex cursor-pointer rounded-full px-2 py-0.5 text-xs font-medium',
              STATUS_COLORS[agent.status] ?? 'bg-muted text-muted-foreground',
            )}
          >
            {agent.status}
          </span>
        )}
      </td>
      <td className="px-4 py-3">
        <span
          className={clsx(
            'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
            RISK_COLORS[agent.riskTier] ?? 'bg-muted text-muted-foreground',
          )}
        >
          {agent.riskTier}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {agent.provider ?? '-'}{agent.model ? ` / ${agent.model}` : ''}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {agent.frameworks.length > 0 ? (
            agent.frameworks.map((f) => (
              <span key={f} className="rounded bg-indigo-50 px-1.5 py-0.5 text-xs text-indigo-700">
                {f}
              </span>
            ))
          ) : (
            <span className="text-xs text-muted-foreground/60">None</span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">{agent.owner ?? '-'}</td>
      <td className="px-4 py-3">
        <div className="flex gap-3">
          <Link
            href={`/dashboard/agents/${agent.id}/policies`}
            className="text-xs font-medium text-primary hover:text-primary"
          >
            Policies
          </Link>
          <button
            onClick={onDelete}
            className="text-xs font-medium text-red-600 hover:text-red-500"
          >
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}

function CreateAgentForm({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [owner, setOwner] = useState('');
  const [riskTier, setRiskTier] = useState('medium');
  const [provider, setProvider] = useState('');
  const [model, setModel] = useState('');
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>([]);

  const mutation = useMutation({
    mutationFn: createAgent,
    onSuccess,
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    mutation.mutate({
      name: name.trim(),
      description: description.trim() || undefined,
      owner: owner.trim() || undefined,
      risk_tier: riskTier,
      provider: provider.trim() || undefined,
      model: model.trim() || undefined,
      frameworks: selectedFrameworks,
    });
  }

  function toggleFramework(f: string) {
    setSelectedFrameworks((prev) =>
      prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f],
    );
  }

  return (
    <div className="mb-6 rounded-xl border border-border bg-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Register New Agent</h3>
        <button onClick={onClose} className="text-xs text-muted-foreground/60 hover:text-muted-foreground">Close</button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              placeholder="Customer Service Agent"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Owner</label>
            <input
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              placeholder="Engineering team"
            />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted-foreground">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-lg border border-border px-3 py-2 text-sm"
            rows={2}
            placeholder="What does this agent do?"
          />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Risk Tier</label>
            <select
              value={riskTier}
              onChange={(e) => setRiskTier(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
            >
              {RISK_TIERS.map((r) => (
                <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Provider</label>
            <input
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              placeholder="openai"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Model</label>
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              placeholder="gpt-4o"
            />
          </div>
        </div>
        <div>
          <label className="mb-2 block text-xs text-muted-foreground">Compliance Frameworks</label>
          <div className="flex flex-wrap gap-2">
            {FRAMEWORKS.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => toggleFramework(f)}
                className={clsx(
                  'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                  selectedFrameworks.includes(f)
                    ? 'bg-indigo-600 text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted',
                )}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={!name.trim() || mutation.isPending}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/100 disabled:opacity-50"
          >
            {mutation.isPending ? 'Registering...' : 'Register Agent'}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
