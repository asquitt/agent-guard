'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listApiKeys, createApiKey, revokeApiKey } from '@/lib/api';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EmptyState } from '@/components/ui/EmptyState';
import { Key } from 'lucide-react';
import type { ApiKey } from '@/types';

export default function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [revokingKey, setRevokingKey] = useState<ApiKey | null>(null);

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
          <h1 className="text-2xl font-bold text-foreground">API Keys</h1>
          <p className="text-sm text-muted-foreground">
            Manage keys for authenticating proxy requests
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/80"
        >
          Create key
        </button>
      </div>

      {/* Created key banner */}
      {createdKey && (
        <div className="mb-4 rounded-xl border border-success-500 bg-green-500/10 p-4">
          <p className="mb-2 text-sm font-medium text-green-400">
            API key created — copy it now, it won&apos;t be shown again
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded bg-card px-3 py-2 text-sm font-mono text-foreground">
              {createdKey}
            </code>
            <button
              onClick={() => handleCopy(createdKey)}
              className="rounded-lg bg-green-500 px-3 py-2 text-sm font-medium text-white hover:bg-green-500/100"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={() => setCreatedKey(null)}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="mb-4 rounded-xl border border-border bg-card p-4">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-foreground">
                Key name
              </label>
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="e.g. Production, Staging"
                className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <button
              onClick={() => createMutation.mutate(newKeyName)}
              disabled={!newKeyName.trim() || createMutation.isPending}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/80 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Keys list */}
      <div className="rounded-xl border border-border bg-card">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : keys.length === 0 ? (
          <EmptyState
            icon={Key}
            title="No API keys"
            description="Create an API key to authenticate proxy requests through AgentGuard."
            action={{ label: 'Create Key', onClick: () => setShowCreate(true) }}
          />
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <th className="px-6 py-3">Name</th>
                <th className="px-6 py-3">Key</th>
                <th className="px-6 py-3">Scopes</th>
                <th className="px-6 py-3">Last Used</th>
                <th className="px-6 py-3">Created</th>
                <th className="px-6 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {keys.map((key) => (
                <ApiKeyRow
                  key={key.id}
                  apiKey={key}
                  onRevoke={() => setRevokingKey(key)}
                  revoking={revokeMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      <ConfirmDialog
        open={!!revokingKey}
        title="Revoke API key"
        description={`Are you sure you want to revoke "${revokingKey?.name ?? ''}"? Any integrations using this key will stop working immediately.`}
        confirmLabel="Revoke"
        variant="danger"
        loading={revokeMutation.isPending}
        onConfirm={() => {
          if (revokingKey) {
            revokeMutation.mutate(revokingKey.id, {
              onSuccess: () => setRevokingKey(null),
            });
          }
        }}
        onCancel={() => setRevokingKey(null)}
      />
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
    <tr className="hover:bg-muted/50">
      <td className="px-6 py-3 text-sm font-medium text-foreground">
        {apiKey.name}
      </td>
      <td className="px-6 py-3">
        <code className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
          {apiKey.prefix}...
        </code>
      </td>
      <td className="px-6 py-3 text-sm text-muted-foreground">
        {apiKey.scopes.join(', ')}
      </td>
      <td className="px-6 py-3 text-sm text-muted-foreground">
        {apiKey.lastUsedAt
          ? new Date(apiKey.lastUsedAt).toLocaleDateString()
          : 'Never'}
      </td>
      <td className="px-6 py-3 text-sm text-muted-foreground">
        {new Date(apiKey.createdAt).toLocaleDateString()}
      </td>
      <td className="px-6 py-3">
        {apiKey.isActive && (
          <button
            onClick={onRevoke}
            disabled={revoking}
            className="text-sm text-red-400 hover:text-red-300 disabled:opacity-50"
          >
            Revoke
          </button>
        )}
        {!apiKey.isActive && (
          <span className="text-xs text-muted-foreground/60">Revoked</span>
        )}
      </td>
    </tr>
  );
}
