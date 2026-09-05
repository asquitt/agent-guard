'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  listSiemFormats,
  listSiemDestinations,
  createSiemDestination,
  updateSiemDestination,
  deleteSiemDestination,
  previewSiemFormat,
} from '@/lib/api/siem';
import type { SiemDestination, SiemFormat } from '@/lib/api/siem';

const SEVERITY_OPTIONS = ['info', 'low', 'medium', 'high', 'critical'];
const EVENT_TYPE_OPTIONS = [
  'incident.created',
  'incident.resolved',
  'incident.escalated',
  'detection.blocked',
  'detection.redacted',
];

export default function SiemSettingsPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [previewFormat, setPreviewFormat] = useState<string | null>(null);
  const [previewOutput, setPreviewOutput] = useState('');

  // Form state
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [format, setFormat] = useState('splunk_hec');
  const [authHeader, setAuthHeader] = useState('');
  const [minSeverity, setMinSeverity] = useState('medium');
  const [eventTypes, setEventTypes] = useState<string[]>(['incident.created', 'incident.resolved']);

  const { data: formats } = useQuery({
    queryKey: ['siem-formats'],
    queryFn: listSiemFormats,
  });

  const { data: destinations, isLoading } = useQuery({
    queryKey: ['siem-destinations'],
    queryFn: () => listSiemDestinations(),
  });

  const createMutation = useMutation({
    mutationFn: createSiemDestination,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['siem-destinations'] });
      setShowCreate(false);
      resetForm();
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      updateSiemDestination(id, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['siem-destinations'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSiemDestination,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['siem-destinations'] }),
  });

  function resetForm() {
    setName('');
    setUrl('');
    setFormat('splunk_hec');
    setAuthHeader('');
    setMinSeverity('medium');
    setEventTypes(['incident.created', 'incident.resolved']);
  }

  async function handlePreview(fmt: string) {
    setPreviewFormat(fmt);
    try {
      const result = await previewSiemFormat(fmt);
      setPreviewOutput(result.output);
    } catch {
      setPreviewOutput('Failed to generate preview');
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    createMutation.mutate({
      name,
      url,
      format,
      auth_header: authHeader || undefined,
      min_severity: minSeverity,
      event_types: eventTypes,
    });
  }

  const formatLabel = (id: string) =>
    formats?.formats.find((f) => f.id === id)?.name ?? id;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          href="/dashboard/settings"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          &larr; Settings
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-foreground">
          SIEM/SOAR Integration
        </h1>
        <p className="text-sm text-muted-foreground">
          Send security events to your SIEM in CEF, OCSF, Splunk HEC, ECS, or LEEF format
        </p>
      </div>

      {/* Supported Formats */}
      <div className="mb-6 rounded-xl border border-border bg-card p-6">
        <h2 className="mb-3 text-sm font-semibold text-foreground">
          Supported Formats
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {formats?.formats.map((f: SiemFormat) => (
            <div
              key={f.id}
              className="flex items-start justify-between rounded-lg border border-border p-3"
            >
              <div>
                <p className="text-sm font-medium text-foreground">{f.name}</p>
                <p className="text-xs text-muted-foreground">{f.description}</p>
              </div>
              <button
                onClick={() => handlePreview(f.id)}
                className="ml-2 shrink-0 rounded-md bg-muted px-2 py-1 text-xs text-foreground hover:bg-muted/80"
              >
                Preview
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Format Preview */}
      {previewFormat && (
        <div className="mb-6 rounded-xl border border-border bg-card p-6">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">
              Preview: {formatLabel(previewFormat)}
            </h2>
            <button
              onClick={() => setPreviewFormat(null)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>
          <pre className="max-h-60 overflow-auto rounded-lg bg-muted p-4 text-xs text-foreground">
            {previewOutput}
          </pre>
        </div>
      )}

      {/* Destinations List */}
      <div className="mb-6 rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">
            SIEM Destinations ({destinations?.total ?? 0})
          </h2>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          >
            {showCreate ? 'Cancel' : '+ Add Destination'}
          </button>
        </div>

        {/* Create Form */}
        {showCreate && (
          <form onSubmit={handleSubmit} className="mb-6 space-y-4 rounded-lg border border-border bg-muted/50 p-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="siem-name" className="mb-1 block text-xs font-medium text-foreground">Name</label>
                <input
                  id="siem-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Production Splunk"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                  required
                />
              </div>
              <div>
                <label htmlFor="siem-format" className="mb-1 block text-xs font-medium text-foreground">Format</label>
                <select
                  id="siem-format"
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                >
                  {formats?.formats.map((f) => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="siem-endpoint-url" className="mb-1 block text-xs font-medium text-foreground">Endpoint URL</label>
                <input
                  id="siem-endpoint-url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://your-siem.example.com/api/events"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                  required
                />
              </div>
              <div>
                <label htmlFor="siem-authorization-header" className="mb-1 block text-xs font-medium text-foreground">
                  Authorization Header <span className="text-muted-foreground">(optional)</span>
                </label>
                <input
                  id="siem-authorization-header"
                  value={authHeader}
                  onChange={(e) => setAuthHeader(e.target.value)}
                  placeholder="e.g. Splunk abc123-token"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                />
              </div>
              <div>
                <label htmlFor="siem-min-severity" className="mb-1 block text-xs font-medium text-foreground">Min Severity</label>
                <select
                  id="siem-min-severity"
                  value={minSeverity}
                  onChange={(e) => setMinSeverity(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                >
                  {SEVERITY_OPTIONS.map((s) => (
                    <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                  ))}
                </select>
              </div>
              <fieldset className="sm:col-span-2">
                <legend className="mb-1 block text-xs font-medium text-foreground">Event Types</legend>
                <div className="flex flex-wrap gap-2">
                  {EVENT_TYPE_OPTIONS.map((evt) => (
                    <label key={evt} className="flex items-center gap-1.5 text-xs text-foreground">
                      <input
                        type="checkbox"
                        checked={eventTypes.includes(evt)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setEventTypes([...eventTypes, evt]);
                          } else {
                            setEventTypes(eventTypes.filter((t) => t !== evt));
                          }
                        }}
                        className="rounded border-border"
                      />
                      {evt}
                    </label>
                  ))}
                </div>
              </fieldset>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => { setShowCreate(false); resetForm(); }}
                className="rounded-md border border-border px-3 py-1.5 text-xs text-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="rounded-md bg-primary px-4 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating...' : 'Create Destination'}
              </button>
            </div>
          </form>
        )}

        {/* Destination List */}
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : destinations?.items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <p className="text-sm text-muted-foreground">
              No SIEM destinations configured. Add one to start receiving security events.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {destinations?.items.map((dest: SiemDestination) => (
              <div
                key={dest.id}
                className="flex items-center justify-between rounded-lg border border-border p-4"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-foreground">{dest.name}</p>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      {formatLabel(dest.format)}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        dest.isActive
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}
                    >
                      {dest.isActive ? 'Active' : 'Paused'}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-muted-foreground">{dest.url}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Min severity: {dest.minSeverity} | Events: {dest.eventTypes.join(', ')}
                  </p>
                </div>
                <div className="ml-4 flex shrink-0 gap-2">
                  <button
                    onClick={() => toggleMutation.mutate({ id: dest.id, isActive: !dest.isActive })}
                    className="rounded-md border border-border px-2 py-1 text-xs text-foreground hover:bg-muted"
                  >
                    {dest.isActive ? 'Pause' : 'Enable'}
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Delete this SIEM destination?')) {
                        deleteMutation.mutate(dest.id);
                      }
                    }}
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

      {/* Integration Guide */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="mb-3 text-sm font-semibold text-foreground">
          Integration Guide
        </h2>
        <div className="space-y-3 text-xs text-muted-foreground">
          <div>
            <p className="font-medium text-foreground">Splunk</p>
            <p>Create an HTTP Event Collector (HEC) token in Splunk, then paste the HEC endpoint URL and set the Authorization header to &quot;Splunk YOUR_TOKEN&quot;.</p>
          </div>
          <div>
            <p className="font-medium text-foreground">Elastic / ELK</p>
            <p>Point to your Elasticsearch ingest endpoint. Events will be formatted in Elastic Common Schema (ECS) for native compatibility.</p>
          </div>
          <div>
            <p className="font-medium text-foreground">IBM QRadar</p>
            <p>Use LEEF format. Configure a Universal REST API log source in QRadar pointing to the AgentGuard SIEM endpoint.</p>
          </div>
          <div>
            <p className="font-medium text-foreground">Microsoft Sentinel</p>
            <p>Use OCSF format with Azure Logic Apps. Create a webhook trigger that posts to the Logs Ingestion API.</p>
          </div>
          <div>
            <p className="font-medium text-foreground">Generic / CEF</p>
            <p>CEF is supported by most SIEMs. Configure a webhook receiver and AgentGuard will deliver events in standard CEF format.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
