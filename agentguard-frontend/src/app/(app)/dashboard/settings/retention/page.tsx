'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  getRetentionPolicy,
  updateRetentionPolicy,
  listArchives,
} from '@/lib/api';
import type { RetentionPolicyUpdate } from '@/types';

const TABLE_LABELS: Record<string, string> = {
  proxy_requests: 'LLM Request Logs',
  incidents: 'Incident Records',
  audit_logs: 'Audit Logs',
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export default function RetentionSettingsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<RetentionPolicyUpdate>({});
  const [saved, setSaved] = useState(false);
  const [tableFilter, setTableFilter] = useState<string | undefined>();

  const {
    data: policy,
    isLoading: policyLoading,
    error: policyError,
  } = useQuery({
    queryKey: ['retention-policy'],
    queryFn: getRetentionPolicy,
  });

  const { data: archivesData, isLoading: archivesLoading } = useQuery({
    queryKey: ['archives', tableFilter],
    queryFn: () => listArchives({ tableName: tableFilter, limit: 50 }),
  });

  const updateMutation = useMutation({
    mutationFn: (data: RetentionPolicyUpdate) => updateRetentionPolicy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['retention-policy'] });
      setForm({});
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const updates: RetentionPolicyUpdate = {};
    if (form.proxyRequestsDays !== undefined)
      updates.proxyRequestsDays = form.proxyRequestsDays;
    if (form.incidentsDays !== undefined)
      updates.incidentsDays = form.incidentsDays;
    if (form.auditLogsDays !== undefined)
      updates.auditLogsDays = form.auditLogsDays;
    if (Object.keys(updates).length > 0) {
      updateMutation.mutate(updates);
    }
  };

  const getValue = (
    field: keyof RetentionPolicyUpdate,
    policyField: 'proxyRequestsDays' | 'incidentsDays' | 'auditLogsDays',
  ) => {
    return form[field] !== undefined ? form[field] : (policy?.[policyField] ?? 0);
  };

  return (
    <div>
      <div className="mb-6">
        <Link
          href="/dashboard/settings"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          &larr; Settings
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-foreground">
          Data Retention
        </h1>
        <p className="text-sm text-muted-foreground">
          Configure how long data is kept in the active database before
          archiving
        </p>
      </div>

      {/* Policy Form */}
      <div className="mb-6 rounded-xl border border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          Retention Policy
        </h2>

        {policyLoading && (
          <p className="text-sm text-muted-foreground/60">Loading policy...</p>
        )}
        {policyError && (
          <p className="text-sm text-red-600">Failed to load policy</p>
        )}

        {policy && (
          <form onSubmit={handleSave} className="space-y-5">
            {(
              [
                {
                  key: 'proxyRequestsDays' as const,
                  label: 'LLM Request Logs',
                  desc: 'Full request/response bodies — high storage volume',
                  rec: 30,
                },
                {
                  key: 'incidentsDays' as const,
                  label: 'Incident Records',
                  desc: 'Detection results and metadata',
                  rec: 365,
                },
                {
                  key: 'auditLogsDays' as const,
                  label: 'Audit Logs',
                  desc: 'User actions and system events — compliance requirement',
                  rec: 365,
                },
              ] as const
            ).map((item) => (
              <div key={item.key}>
                <label className="block text-sm font-medium text-foreground">
                  {item.label}
                </label>
                <p className="mb-1 text-xs text-muted-foreground/60">{item.desc}</p>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min={0}
                    max={3650}
                    className="w-28 rounded-lg border border-border px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    value={getValue(item.key, item.key)}
                    onChange={(e) =>
                      setForm({ ...form, [item.key]: parseInt(e.target.value) || 0 })
                    }
                  />
                  <span className="text-sm text-muted-foreground">days</span>
                  <span className="text-xs text-muted-foreground/60">
                    (recommended: {item.rec})
                  </span>
                </div>
              </div>
            ))}

            {saved && (
              <p className="text-sm font-medium text-green-600">
                Policy saved successfully
              </p>
            )}
            {updateMutation.isError && (
              <p className="text-sm text-red-600">
                Failed to save — please try again
              </p>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={
                  updateMutation.isPending || Object.keys(form).length === 0
                }
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/80 disabled:opacity-50"
              >
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
              {Object.keys(form).length > 0 && (
                <button
                  type="button"
                  onClick={() => setForm({})}
                  className="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted/50"
                >
                  Reset
                </button>
              )}
            </div>
          </form>
        )}
      </div>

      {/* Info Card */}
      <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50 p-4">
        <h3 className="text-sm font-semibold text-blue-900">
          How Retention Works
        </h3>
        <ul className="mt-2 space-y-1 text-sm text-blue-800">
          <li>
            Data older than the retention period is archived nightly at 3:30 AM
            UTC
          </li>
          <li>
            Archived data is compressed (JSONL.gz) and stored for compliance
          </li>
          <li>Set retention to 0 to disable automatic archival for a type</li>
        </ul>
      </div>

      {/* Archives Table */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Archives</h2>
          <div className="flex gap-2">
            {[undefined, 'proxy_requests', 'incidents', 'audit_logs'].map(
              (t) => (
                <button
                  key={t ?? 'all'}
                  onClick={() => setTableFilter(t)}
                  className={`rounded-lg px-3 py-1 text-xs font-medium ${
                    tableFilter === t
                      ? 'bg-primary/10 text-primary'
                      : 'bg-muted text-muted-foreground hover:bg-muted'
                  }`}
                >
                  {t ? TABLE_LABELS[t] : 'All'}
                </button>
              ),
            )}
          </div>
        </div>

        {archivesLoading && (
          <p className="py-8 text-center text-sm text-muted-foreground/60">
            Loading archives...
          </p>
        )}

        {archivesData && archivesData.items.length === 0 && (
          <div className="py-12 text-center text-muted-foreground/60">
            <p className="text-lg">No archives yet</p>
            <p className="mt-1 text-sm">
              Archives are created automatically based on your retention policy
            </p>
          </div>
        )}

        {archivesData && archivesData.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs font-medium uppercase text-muted-foreground">
                  <th className="pb-2 pr-4">Type</th>
                  <th className="pb-2 pr-4">Date Range</th>
                  <th className="pb-2 pr-4">Records</th>
                  <th className="pb-2 pr-4">Size</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {archivesData.items.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-border last:border-0"
                  >
                    <td className="py-2 pr-4 font-medium text-foreground">
                      {TABLE_LABELS[a.tableName] ?? a.tableName}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {new Date(a.startDate).toLocaleDateString()} &ndash;{' '}
                      {new Date(a.endDate).toLocaleDateString()}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {a.rowCount.toLocaleString()}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {formatBytes(a.fileSizeBytes)}
                    </td>
                    <td className="py-2 pr-4">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          a.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : a.status === 'failed'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {a.status}
                      </span>
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {new Date(a.createdAt).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-muted-foreground/60">
              {archivesData.total} total archive(s)
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
