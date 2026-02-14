'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listModels,
  getModelSummary,
  createModel,
  updateModel,
  deleteModel,
} from '@/lib/api/model-registry';
import type { AIModel, AIModelCreate } from '@/lib/api/model-registry';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { useToast } from '@/hooks/useToast';

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const STATUS_COLORS: Record<string, string> = {
  approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

export default function ModelRegistryPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [showCreate, setShowCreate] = useState(false);
  const [filterProvider, setFilterProvider] = useState('');
  const [filterRisk, setFilterRisk] = useState('');
  const [deletingModel, setDeletingModel] = useState<AIModel | null>(null);

  // Form state
  const [form, setForm] = useState<AIModelCreate>({
    model_name: '',
    provider: '',
    model_version: 'latest',
    model_type: 'llm',
    risk_level: 'medium',
    pii_handling: 'strict',
    capabilities: [],
    risk_factors: [],
    compliance_frameworks: [],
  });

  const { data: summary } = useQuery({
    queryKey: ['model-registry-summary'],
    queryFn: getModelSummary,
  });

  const { data: models, isLoading } = useQuery({
    queryKey: ['model-registry', filterProvider, filterRisk],
    queryFn: () =>
      listModels({
        provider: filterProvider || undefined,
        riskLevel: filterRisk || undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: createModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-registry'] });
      queryClient.invalidateQueries({ queryKey: ['model-registry-summary'] });
      setShowCreate(false);
      setForm({
        model_name: '',
        provider: '',
        model_version: 'latest',
        model_type: 'llm',
        risk_level: 'medium',
        pii_handling: 'strict',
        capabilities: [],
        risk_factors: [],
        compliance_frameworks: [],
      });
      toast.success('Model registered');
    },
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateModel(id, { approval_status: status }),
    onSuccess: (_data, { status }) => {
      queryClient.invalidateQueries({ queryKey: ['model-registry'] });
      queryClient.invalidateQueries({ queryKey: ['model-registry-summary'] });
      toast.success(`Model ${status}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-registry'] });
      queryClient.invalidateQueries({ queryKey: ['model-registry-summary'] });
      toast.success('Model deleted');
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    createMutation.mutate(form);
  }

  const providers = summary?.byProvider ? Object.keys(summary.byProvider) : [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">AI Model Registry</h1>
        <p className="text-sm text-muted-foreground">
          Track AI models, provenance, risk profiles, and supply chain dependencies
        </p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <SummaryCard label="Total Models" value={summary.totalModels} />
          <SummaryCard label="Approved" value={summary.approved} color="text-green-600" />
          <SummaryCard label="Pending Review" value={summary.pending} color="text-yellow-600" />
          <SummaryCard label="Deprecated" value={summary.deprecated} color="text-red-600" />
        </div>
      )}

      {/* Risk Distribution */}
      {summary && Object.keys(summary.byRiskLevel).length > 0 && (
        <div className="mb-6 rounded-xl border border-border bg-card p-4">
          <h2 className="mb-2 text-xs font-semibold text-muted-foreground uppercase">
            Risk Distribution
          </h2>
          <div className="flex gap-3">
            {['low', 'medium', 'high', 'critical'].map((level) => {
              const count = summary.byRiskLevel[level] ?? 0;
              if (count === 0) return null;
              return (
                <span
                  key={level}
                  className={`rounded-full px-3 py-1 text-xs font-medium ${RISK_COLORS[level]}`}
                >
                  {level}: {count}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Filters + Actions */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          value={filterProvider}
          onChange={(e) => setFilterProvider(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-xs text-foreground"
        >
          <option value="">All Providers</option>
          {providers.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <select
          value={filterRisk}
          onChange={(e) => setFilterRisk(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-xs text-foreground"
        >
          <option value="">All Risk Levels</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <div className="ml-auto">
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          >
            {showCreate ? 'Cancel' : '+ Register Model'}
          </button>
        </div>
      </div>

      {/* Create Form */}
      {showCreate && (
        <form
          onSubmit={handleSubmit}
          className="mb-6 space-y-4 rounded-xl border border-border bg-card p-6"
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField
              label="Model Name"
              value={form.model_name}
              onChange={(v) => setForm({ ...form, model_name: v })}
              placeholder="e.g. GPT-4 Turbo"
              required
            />
            <FormField
              label="Provider"
              value={form.provider}
              onChange={(v) => setForm({ ...form, provider: v })}
              placeholder="e.g. OpenAI"
              required
            />
            <FormField
              label="Version"
              value={form.model_version ?? 'latest'}
              onChange={(v) => setForm({ ...form, model_version: v })}
            />
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Risk Level</label>
              <select
                value={form.risk_level}
                onChange={(e) => setForm({ ...form, risk_level: e.target.value })}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">PII Handling</label>
              <select
                value={form.pii_handling}
                onChange={(e) => setForm({ ...form, pii_handling: e.target.value })}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
              >
                <option value="strict">Strict</option>
                <option value="limited">Limited</option>
                <option value="unfiltered">Unfiltered</option>
              </select>
            </div>
            <FormField
              label="Owner Email"
              value={form.owner_email ?? ''}
              onChange={(v) => setForm({ ...form, owner_email: v })}
              placeholder="team@company.com"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded-md border border-border px-3 py-1.5 text-xs text-foreground hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-md bg-primary px-4 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Registering...' : 'Register Model'}
            </button>
          </div>
        </form>
      )}

      {/* Model List */}
      <div className="rounded-xl border border-border bg-card">
        {isLoading ? (
          <p className="p-6 text-sm text-muted-foreground">Loading...</p>
        ) : models?.items.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-muted-foreground">
              No models registered yet. Register your first model to start tracking AI supply chain.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {models?.items.map((m: AIModel) => (
              <div key={m.id} className="flex items-center justify-between p-4">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-foreground">
                      {m.modelName}
                    </p>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      v{m.modelVersion}
                    </span>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      {m.provider}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                        RISK_COLORS[m.riskLevel] ?? RISK_COLORS.medium
                      }`}
                    >
                      {m.riskLevel} risk
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                        STATUS_COLORS[m.approvalStatus] ?? STATUS_COLORS.pending
                      }`}
                    >
                      {m.approvalStatus}
                    </span>
                    {m.isDeprecated && (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] text-red-700 dark:bg-red-900/30 dark:text-red-400">
                        Deprecated
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                    <span>{m.totalRequests.toLocaleString()} requests</span>
                    <span>{m.totalIncidents} incidents</span>
                    {m.capabilities.length > 0 && (
                      <span>Capabilities: {m.capabilities.slice(0, 3).join(', ')}</span>
                    )}
                  </div>
                </div>
                <div className="ml-4 flex shrink-0 gap-2">
                  {m.approvalStatus === 'pending' && (
                    <button
                      onClick={() => approveMutation.mutate({ id: m.id, status: 'approved' })}
                      className="rounded-md bg-green-100 px-2 py-1 text-xs text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400"
                    >
                      Approve
                    </button>
                  )}
                  <button
                    onClick={() => setDeletingModel(m)}
                    className="rounded-md border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deletingModel}
        title="Delete Model"
        description={`Permanently delete "${deletingModel?.modelName ?? ''}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        loading={deleteMutation.isPending}
        onConfirm={() => {
          if (deletingModel) {
            deleteMutation.mutate(deletingModel.id, {
              onSuccess: () => setDeletingModel(null),
            });
          }
        }}
        onCancel={() => setDeletingModel(null)}
      />
    </div>
  );
}

function SummaryCard({
  label,
  value,
  color = 'text-foreground',
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function FormField({
  label,
  value,
  onChange,
  placeholder,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-foreground">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
        required={required}
      />
    </div>
  );
}
