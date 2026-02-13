'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  listDestinations,
  createDestination,
  updateDestination,
  deleteDestination,
  testDestination,
} from '@/lib/api';
import type { AlertDestination } from '@/types';

const DEST_TYPE_LABELS: Record<string, string> = {
  slack: 'Slack',
  pagerduty: 'PagerDuty',
  email: 'Email',
  webhook: 'Webhook',
};

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState('slack');
  const [newWebhookUrl, setNewWebhookUrl] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['alert-destinations'],
    queryFn: () => listDestinations(),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createDestination({
        name: newName,
        destination_type: newType,
        config: newWebhookUrl ? { webhook_url: newWebhookUrl } : {},
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-destinations'] });
      setShowCreate(false);
      setNewName('');
      setNewWebhookUrl('');
    },
  });

  const destinations = data?.items ?? [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Alert Destinations
          </h1>
          <p className="text-sm text-muted-foreground">
            Configure where incident alerts are sent
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/80"
        >
          Add destination
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="mb-4 rounded-xl border border-border bg-card p-4">
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium text-foreground">
                  Name
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. #incidents-critical"
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-foreground">
                  Type
                </label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="rounded-lg border border-border px-3 py-2 text-sm"
                >
                  <option value="slack">Slack</option>
                  <option value="pagerduty">PagerDuty</option>
                  <option value="email">Email</option>
                  <option value="webhook">Webhook</option>
                </select>
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-foreground">
                Webhook URL
              </label>
              <input
                type="url"
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
                placeholder="https://hooks.slack.com/..."
                className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => createMutation.mutate()}
                disabled={!newName.trim() || createMutation.isPending}
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
        </div>
      )}

      {/* Destinations list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : destinations.length === 0 ? (
        <div className="rounded-xl border border-border bg-card py-16 text-center">
          <p className="text-sm text-muted-foreground">No alert destinations configured</p>
        </div>
      ) : (
        <div className="space-y-4">
          {destinations.map((d) => (
            <DestinationCard key={d.id} destination={d} />
          ))}
        </div>
      )}
    </div>
  );
}

function DestinationCard({ destination }: { destination: AlertDestination }) {
  const queryClient = useQueryClient();
  const [testResult, setTestResult] = useState<string | null>(null);

  const toggleMutation = useMutation({
    mutationFn: (active: boolean) =>
      updateDestination(destination.id, { is_active: active }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['alert-destinations'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteDestination(destination.id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['alert-destinations'] }),
  });

  const testMutation = useMutation({
    mutationFn: () => testDestination(destination.id),
    onSuccess: (resp) => setTestResult(resp.message ?? 'Test sent'),
    onError: () => setTestResult('Test failed'),
  });

  const webhookUrl =
    destination.config && typeof destination.config.webhook_url === 'string'
      ? destination.config.webhook_url
      : null;

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-foreground">
              {destination.name}
            </h3>
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              {DEST_TYPE_LABELS[destination.destinationType] ??
                destination.destinationType}
            </span>
          </div>
          {webhookUrl && (
            <p className="mt-1 text-sm text-muted-foreground truncate max-w-md">
              {webhookUrl}
            </p>
          )}
        </div>

        <button
          onClick={() => toggleMutation.mutate(!destination.isActive)}
          disabled={toggleMutation.isPending}
          className={clsx(
            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
            destination.isActive ? 'bg-primary' : 'bg-muted',
          )}
        >
          <span
            className={clsx(
              'inline-block h-4 w-4 rounded-full bg-card transition-transform',
              destination.isActive ? 'translate-x-6' : 'translate-x-1',
            )}
          />
        </button>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <button
          onClick={() => testMutation.mutate()}
          disabled={testMutation.isPending}
          className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted/50 disabled:opacity-50"
        >
          {testMutation.isPending ? 'Sending...' : 'Send test'}
        </button>
        <button
          onClick={() => {
            if (confirm('Delete this destination?')) {
              deleteMutation.mutate();
            }
          }}
          disabled={deleteMutation.isPending}
          className="text-sm text-red-400 hover:text-red-300 disabled:opacity-50"
        >
          Delete
        </button>
        {testResult && (
          <span className="text-sm text-muted-foreground">{testResult}</span>
        )}
      </div>
    </div>
  );
}
