'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  getAgent,
  listPolicies,
  createPolicy,
  deletePolicy,
  listPolicyTemplates,
} from '@/lib/api';
import type { AgentPolicy, PolicyCreateData, PolicyTemplate } from '@/lib/api';

export default function AgentPoliciesPage() {
  const params = useParams();
  const router = useRouter();
  const agentId = params.agentId as string;
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState<AgentPolicy | null>(null);

  const { data: agent } = useQuery({
    queryKey: ['agents', agentId],
    queryFn: () => getAgent(agentId),
  });

  const { data: policiesData, isLoading } = useQuery({
    queryKey: ['agent-policies', agentId],
    queryFn: () => listPolicies(agentId, { limit: 100 }),
  });

  const deleteMutation = useMutation({
    mutationFn: (policyId: string) => deletePolicy(agentId, policyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agent-policies', agentId] }),
  });

  const policies = policiesData?.items ?? [];

  return (
    <div>
      <div className="mb-6">
        <button
          onClick={() => router.push('/dashboard/agents')}
          className="mb-2 text-xs text-primary-600 hover:text-primary-500"
        >
          &larr; Back to Agents
        </button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Behavior Policies {agent ? `— ${agent.name}` : ''}
            </h1>
            <p className="text-sm text-gray-500">
              Define what this agent can and cannot do
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500"
          >
            New Policy
          </button>
        </div>
      </div>

      {showCreate && (
        <CreatePolicyForm
          agentId={agentId}
          onClose={() => setShowCreate(false)}
          onSuccess={() => {
            setShowCreate(false);
            queryClient.invalidateQueries({ queryKey: ['agent-policies', agentId] });
          }}
        />
      )}

      {selectedPolicy && (
        <PolicyDetail
          policy={selectedPolicy}
          onClose={() => setSelectedPolicy(null)}
        />
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        </div>
      ) : policies.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
          <p className="text-sm text-gray-500">No policies defined yet</p>
          <p className="mt-1 text-xs text-gray-400">
            Create a policy or start from a template to govern agent behavior
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {policies.map((p) => (
            <PolicyCard
              key={p.id}
              policy={p}
              onSelect={() => setSelectedPolicy(p)}
              onDelete={() => deleteMutation.mutate(p.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function PolicyCard({
  policy,
  onSelect,
  onDelete,
}: {
  policy: AgentPolicy;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const ruleCount =
    policy.allowedTopics.length +
    policy.forbiddenTopics.length +
    policy.approvedTools.length +
    policy.requiredDisclosures.length +
    policy.customRules.length +
    (policy.maxTransactionAmount ? 1 : 0);

  return (
    <div
      onClick={onSelect}
      className="cursor-pointer rounded-xl border border-gray-200 bg-white p-6 hover:border-primary-200 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900">{policy.name}</h3>
            <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-600">
              v{policy.version}
            </span>
          </div>
          {policy.description && (
            <p className="mt-1 text-sm text-gray-500">{policy.description}</p>
          )}
          <p className="mt-2 text-xs text-gray-400">
            {ruleCount} rule{ruleCount !== 1 ? 's' : ''} · Created{' '}
            {new Date(policy.createdAt).toLocaleDateString()}
          </p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="text-xs font-medium text-red-600 hover:text-red-500"
        >
          Delete
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {policy.forbiddenTopics.length > 0 && (
          <span className="rounded bg-red-50 px-2 py-1 text-xs text-red-600">
            {policy.forbiddenTopics.length} forbidden topic{policy.forbiddenTopics.length !== 1 ? 's' : ''}
          </span>
        )}
        {policy.allowedTopics.length > 0 && (
          <span className="rounded bg-green-50 px-2 py-1 text-xs text-green-600">
            {policy.allowedTopics.length} allowed topic{policy.allowedTopics.length !== 1 ? 's' : ''}
          </span>
        )}
        {policy.approvedTools.length > 0 && (
          <span className="rounded bg-blue-50 px-2 py-1 text-xs text-blue-600">
            {policy.approvedTools.length} approved tool{policy.approvedTools.length !== 1 ? 's' : ''}
          </span>
        )}
        {policy.maxTransactionAmount && (
          <span className="rounded bg-yellow-50 px-2 py-1 text-xs text-yellow-700">
            Max {policy.maxTransactionAmount.currency} {policy.maxTransactionAmount.amount.toLocaleString()}
          </span>
        )}
        {policy.requiredDisclosures.length > 0 && (
          <span className="rounded bg-purple-50 px-2 py-1 text-xs text-purple-600">
            {policy.requiredDisclosures.length} disclosure{policy.requiredDisclosures.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>
    </div>
  );
}

function PolicyDetail({ policy, onClose }: { policy: AgentPolicy; onClose: () => void }) {
  return (
    <div className="mb-6 rounded-xl border border-primary-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">
          {policy.name} <span className="text-gray-400">v{policy.version}</span>
        </h3>
        <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600">Close</button>
      </div>

      <div className="space-y-4">
        {policy.allowedTopics.length > 0 && (
          <RuleSection label="Allowed Topics" items={policy.allowedTopics} color="green" />
        )}
        {policy.forbiddenTopics.length > 0 && (
          <RuleSection label="Forbidden Topics" items={policy.forbiddenTopics} color="red" />
        )}
        {policy.maxTransactionAmount && (
          <div>
            <p className="mb-1 text-xs font-medium uppercase text-gray-500">Transaction Limit</p>
            <span className="inline-flex rounded bg-yellow-50 px-2 py-1 text-xs text-yellow-700">
              {policy.maxTransactionAmount.currency} {policy.maxTransactionAmount.amount.toLocaleString()}
            </span>
          </div>
        )}
        {policy.requiredDisclosures.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-medium uppercase text-gray-500">Required Disclosures</p>
            <ul className="space-y-1">
              {policy.requiredDisclosures.map((d, i) => (
                <li key={i} className="rounded bg-purple-50 px-3 py-2 text-xs text-purple-700">{d}</li>
              ))}
            </ul>
          </div>
        )}
        {policy.approvedDataSources.length > 0 && (
          <RuleSection label="Approved Data Sources" items={policy.approvedDataSources} color="indigo" />
        )}
        {policy.approvedTools.length > 0 && (
          <RuleSection label="Approved Tools" items={policy.approvedTools} color="blue" />
        )}
        {policy.customRules.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-medium uppercase text-gray-500">Custom Rules</p>
            <ul className="space-y-1">
              {policy.customRules.map((r, i) => (
                <li key={i} className="rounded bg-gray-50 px-3 py-2 text-xs text-gray-600">
                  <span className="font-medium">{r.rule}:</span> {r.description}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function RuleSection({ label, items, color }: { label: string; items: string[]; color: string }) {
  const colorMap: Record<string, string> = {
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-700',
    blue: 'bg-blue-50 text-blue-700',
    indigo: 'bg-indigo-50 text-indigo-700',
  };
  return (
    <div>
      <p className="mb-1 text-xs font-medium uppercase text-gray-500">{label}</p>
      <div className="flex flex-wrap gap-1">
        {items.map((item) => (
          <span
            key={item}
            className={clsx('rounded px-2 py-1 text-xs', colorMap[color] ?? 'bg-gray-50 text-gray-600')}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function CreatePolicyForm({
  agentId,
  onClose,
  onSuccess,
}: {
  agentId: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [allowedTopics, setAllowedTopics] = useState('');
  const [forbiddenTopics, setForbiddenTopics] = useState('');
  const [maxAmount, setMaxAmount] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [disclosures, setDisclosures] = useState('');
  const [dataSources, setDataSources] = useState('');
  const [tools, setTools] = useState('');

  const { data: templates } = useQuery({
    queryKey: ['policy-templates'],
    queryFn: listPolicyTemplates,
  });

  const mutation = useMutation({
    mutationFn: (data: PolicyCreateData) => createPolicy(agentId, data),
    onSuccess,
  });

  function applyTemplate(template: PolicyTemplate) {
    const p = template.policy;
    setName(template.name);
    setDescription(template.description);
    setAllowedTopics((p.allowed_topics ?? []).join(', '));
    setForbiddenTopics((p.forbidden_topics ?? []).join(', '));
    if (p.max_transaction_amount) {
      setMaxAmount(String(p.max_transaction_amount.amount));
      setCurrency(p.max_transaction_amount.currency);
    }
    setDisclosures((p.required_disclosures ?? []).join('\n'));
    setDataSources((p.approved_data_sources ?? []).join(', '));
    setTools((p.approved_tools ?? []).join(', '));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    const split = (s: string) =>
      s.split(',').map((x) => x.trim()).filter(Boolean);

    const data: PolicyCreateData = {
      name: name.trim(),
      description: description.trim() || undefined,
      allowed_topics: split(allowedTopics),
      forbidden_topics: split(forbiddenTopics),
      max_transaction_amount: maxAmount
        ? { currency, amount: parseFloat(maxAmount) }
        : undefined,
      required_disclosures: disclosures
        .split('\n')
        .map((x) => x.trim())
        .filter(Boolean),
      approved_data_sources: split(dataSources),
      approved_tools: split(tools),
    };
    mutation.mutate(data);
  }

  return (
    <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">New Behavior Policy</h3>
        <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600">Close</button>
      </div>

      {templates && templates.length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs font-medium text-gray-500">Start from a template:</p>
          <div className="flex flex-wrap gap-2">
            {templates.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => applyTemplate(t)}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs text-gray-500">Policy Name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="Customer Service Policy"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Description</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="What does this policy enforce?"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs text-gray-500">Allowed Topics (comma-separated)</label>
            <input
              value={allowedTopics}
              onChange={(e) => setAllowedTopics(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="account_balance, product_info, faq"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Forbidden Topics (comma-separated)</label>
            <input
              value={forbiddenTopics}
              onChange={(e) => setForbiddenTopics(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="investment_advice, legal_opinions"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="mb-1 block text-xs text-gray-500">Max Transaction Amount</label>
            <input
              value={maxAmount}
              onChange={(e) => setMaxAmount(e.target.value)}
              type="number"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="10000"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Currency</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="GBP">GBP</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Approved Tools (comma-separated)</label>
            <input
              value={tools}
              onChange={(e) => setTools(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="lookup_account, search_faq"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs text-gray-500">Approved Data Sources (comma-separated)</label>
          <input
            value={dataSources}
            onChange={(e) => setDataSources(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            placeholder="customer_account_api, product_catalog"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs text-gray-500">Required Disclosures (one per line)</label>
          <textarea
            value={disclosures}
            onChange={(e) => setDisclosures(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            placeholder="I am an AI assistant and cannot provide financial advice."
          />
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={!name.trim() || mutation.isPending}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500 disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating...' : 'Create Policy'}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
