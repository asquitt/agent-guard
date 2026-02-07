'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listApiKeys, createApiKey, revokeApiKey } from '@/lib/api';
import type { ApiKey } from '@/types';

export default function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => listApiKeys(),
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => createApiKey({ name }),
    onSuccess: (resp) => {
      setCreatedKey(resp.key);
      setNewKeyName('');
      setShowCreate(false);
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => revokeApiKey(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['api-keys'] }),
  });

  const keys = data?.items ?? [];

  function handleCopy(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
          <p className="text-sm text-gray-500">
            Manage keys for authenticating proxy requests
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Create key
        </button>
      </div>

      {/* Created key banner */}
      {createdKey && (
        <div className="mb-4 rounded-xl border border-success-500 bg-success-50 p-4">
          <p className="mb-2 text-sm font-medium text-success-600">
            API key created — copy it now, it won&apos;t be shown again
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded bg-white px-3 py-2 text-sm font-mono text-gray-900">
              {createdKey}
            </code>
            <button
              onClick={() => handleCopy(createdKey)}
              className="rounded-lg bg-success-600 px-3 py-2 text-sm font-medium text-white hover:bg-success-500"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={() => setCreatedKey(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Key name
              </label>
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="e.g. Production, Staging"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
            <button
              onClick={() => createMutation.mutate(newKeyName)}
              disabled={!newKeyName.trim() || createMutation.isPending}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Keys list */}
      <div className="rounded-xl border border-gray-200 bg-white">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
          </div>
        ) : keys.length === 0 ? (
          <div className="py-16 text-center text-sm text-gray-500">
            No API keys yet
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-6 py-3">Name</th>
                <th className="px-6 py-3">Key</th>
                <th className="px-6 py-3">Scopes</th>
                <th className="px-6 py-3">Last Used</th>
                <th className="px-6 py-3">Created</th>
                <th className="px-6 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {keys.map((key) => (
                <ApiKeyRow
                  key={key.id}
                  apiKey={key}
                  onRevoke={() => revokeMutation.mutate(key.id)}
                  revoking={revokeMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function ApiKeyRow({
  apiKey,
  onRevoke,
  revoking,
}: {
  apiKey: ApiKey;
  onRevoke: () => void;
  revoking: boolean;
}) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-3 text-sm font-medium text-gray-900">
        {apiKey.name}
      </td>
      <td className="px-6 py-3">
        <code className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          {apiKey.prefix}...
        </code>
      </td>
      <td className="px-6 py-3 text-sm text-gray-600">
        {apiKey.scopes.join(', ')}
      </td>
      <td className="px-6 py-3 text-sm text-gray-500">
        {apiKey.lastUsedAt
          ? new Date(apiKey.lastUsedAt).toLocaleDateString()
          : 'Never'}
      </td>
      <td className="px-6 py-3 text-sm text-gray-500">
        {new Date(apiKey.createdAt).toLocaleDateString()}
      </td>
      <td className="px-6 py-3">
        {apiKey.isActive && (
          <button
            onClick={onRevoke}
            disabled={revoking}
            className="text-sm text-danger-600 hover:text-danger-500 disabled:opacity-50"
          >
            Revoke
          </button>
        )}
        {!apiKey.isActive && (
          <span className="text-xs text-gray-400">Revoked</span>
        )}
      </td>
    </tr>
  );
}
