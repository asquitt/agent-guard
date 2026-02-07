'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  listAuditLogs,
  verifyAuditChain,
  createComplianceReport,
  listComplianceReports,
  getReportDownloadUrl,
} from '@/lib/api';
import { ComplianceScoreboard } from '@/components/dashboard/ComplianceScoreboard';
import type { AuditLogEntry, AuditLogFilters, ComplianceReport } from '@/types';

const PAGE_SIZE = 20;

const REPORT_TYPES = [
  { value: 'access_audit', label: 'Access Audit' },
  { value: 'incident_summary', label: 'Incident Summary' },
  { value: 'detection_efficacy', label: 'Detection Efficacy' },
  { value: 'configuration_changes', label: 'Configuration Changes' },
];

export default function CompliancePage() {
  const [tab, setTab] = useState<'audit' | 'reports'>('audit');

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Compliance</h1>
        <p className="text-sm text-gray-500">Framework scoreboard, audit logs, and compliance reports</p>
      </div>

      <ComplianceScoreboard />

      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1">
        <button
          onClick={() => setTab('audit')}
          className={clsx(
            'rounded-md px-4 py-2 text-sm font-medium transition-colors',
            tab === 'audit' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900',
          )}
        >
          Audit Log
        </button>
        <button
          onClick={() => setTab('reports')}
          className={clsx(
            'rounded-md px-4 py-2 text-sm font-medium transition-colors',
            tab === 'reports' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900',
          )}
        >
          Reports
        </button>
      </div>

      {tab === 'audit' ? <AuditLogTab /> : <ReportsTab />}
    </div>
  );
}

function AuditLogTab() {
  const [filters, setFilters] = useState<AuditLogFilters>({ limit: PAGE_SIZE });

  const { data, isLoading } = useQuery({
    queryKey: ['auditLogs', filters],
    queryFn: () => listAuditLogs(filters),
  });

  const verifyMutation = useMutation({ mutationFn: verifyAuditChain });

  const logs = data?.items ?? [];
  const total = data?.total ?? 0;
  const page = Math.floor((filters.skip ?? 0) / PAGE_SIZE);
  const totalPages = Math.ceil(total / PAGE_SIZE);

  function updateFilter(key: keyof AuditLogFilters, value: string) {
    setFilters((f) => ({ ...f, [key]: value || undefined, skip: 0 }));
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          value={filters.action ?? ''}
          onChange={(e) => updateFilter('action', e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All actions</option>
          <option value="auth.login">Login</option>
          <option value="auth.register">Register</option>
          <option value="auth.logout">Logout</option>
          <option value="auth.login_failed">Login Failed</option>
          <option value="detector.created">Detector Created</option>
          <option value="detector.updated">Detector Updated</option>
          <option value="detector.deleted">Detector Deleted</option>
          <option value="incident.status_changed">Incident Status Changed</option>
          <option value="api_key.created">API Key Created</option>
          <option value="api_key.revoked">API Key Revoked</option>
          <option value="sso_config.created">SSO Config Created</option>
          <option value="webhook.created">Webhook Created</option>
        </select>
        <select
          value={filters.resourceType ?? ''}
          onChange={(e) => updateFilter('resourceType', e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All resources</option>
          <option value="user">User</option>
          <option value="detector">Detector</option>
          <option value="incident">Incident</option>
          <option value="alert_destination">Alert Destination</option>
          <option value="api_key">API Key</option>
          <option value="sso_config">SSO Config</option>
          <option value="webhook">Webhook</option>
          <option value="compliance_report">Compliance Report</option>
        </select>
        <button
          onClick={() => verifyMutation.mutate()}
          disabled={verifyMutation.isPending}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500 disabled:opacity-50"
        >
          {verifyMutation.isPending ? 'Verifying...' : 'Verify Integrity'}
        </button>
        {verifyMutation.data && (
          <span
            className={clsx(
              'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
              verifyMutation.data.valid
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-700',
            )}
          >
            {verifyMutation.data.valid
              ? `Valid (${verifyMutation.data.checked} entries)`
              : `Broken at ${verifyMutation.data.brokenAt}`}
          </span>
        )}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center text-sm text-gray-500">No audit logs found</div>
        ) : (
          <>
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Resource</th>
                  <th className="px-4 py-3">IP Address</th>
                  <th className="px-4 py-3">User ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {logs.map((log) => (
                  <AuditLogRow key={log.id} log={log} />
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3">
                <button
                  disabled={page === 0}
                  onClick={() => setFilters((f) => ({ ...f, skip: Math.max(0, (f.skip ?? 0) - PAGE_SIZE) }))}
                  className="rounded-lg px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-500">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  disabled={page >= totalPages - 1}
                  onClick={() => setFilters((f) => ({ ...f, skip: (f.skip ?? 0) + PAGE_SIZE }))}
                  className="rounded-lg px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function AuditLogRow({ log }: { log: AuditLogEntry }) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-sm text-gray-500">
        {new Date(log.createdAt).toLocaleString()}
      </td>
      <td className="px-4 py-3 text-sm font-medium text-gray-900">{log.action}</td>
      <td className="px-4 py-3 text-sm text-gray-600">
        {log.resourceType}
        {log.resourceId && <span className="ml-1 text-gray-400">{log.resourceId.slice(0, 8)}...</span>}
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">{log.ipAddress ?? '-'}</td>
      <td className="px-4 py-3 text-sm text-gray-500">
        {log.userId ? `${log.userId.slice(0, 8)}...` : '-'}
      </td>
    </tr>
  );
}

function ReportsTab() {
  const queryClient = useQueryClient();
  const [reportType, setReportType] = useState('access_audit');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const { data: reportsData, isLoading } = useQuery({
    queryKey: ['complianceReports'],
    queryFn: listComplianceReports,
    refetchInterval: 5000,
  });

  const createMutation = useMutation({
    mutationFn: createComplianceReport,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['complianceReports'] }),
  });

  const reports = reportsData?.items ?? [];

  function handleGenerate() {
    if (!dateFrom || !dateTo) return;
    createMutation.mutate({ report_type: reportType, date_from: dateFrom, date_to: dateTo });
  }

  return (
    <div>
      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-sm font-medium text-gray-900">Generate Report</h3>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1 block text-xs text-gray-500">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {REPORT_TYPES.map((rt) => (
                <option key={rt.value} value={rt.value}>{rt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={handleGenerate}
            disabled={!dateFrom || !dateTo || createMutation.isPending}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500 disabled:opacity-50"
          >
            {createMutation.isPending ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
          </div>
        ) : reports.length === 0 ? (
          <div className="py-16 text-center text-sm text-gray-500">No reports generated yet</div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Period</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reports.map((report) => (
                <ReportRow key={report.id} report={report} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function ReportRow({ report }: { report: ComplianceReport }) {
  const typeLabel = REPORT_TYPES.find((rt) => rt.value === report.reportType)?.label ?? report.reportType;

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-sm font-medium text-gray-900">{typeLabel}</td>
      <td className="px-4 py-3 text-sm text-gray-600">
        {new Date(report.dateFrom).toLocaleDateString()} - {new Date(report.dateTo).toLocaleDateString()}
      </td>
      <td className="px-4 py-3">
        <span
          className={clsx(
            'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
            report.status === 'completed' && 'bg-green-100 text-green-700',
            report.status === 'pending' && 'bg-yellow-100 text-yellow-700',
            report.status === 'generating' && 'bg-blue-100 text-blue-700',
            report.status === 'failed' && 'bg-red-100 text-red-700',
          )}
        >
          {report.status}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">
        {report.fileSizeBytes ? `${(report.fileSizeBytes / 1024).toFixed(1)} KB` : '-'}
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">
        {new Date(report.createdAt).toLocaleString()}
      </td>
      <td className="px-4 py-3">
        {report.status === 'completed' ? (
          <a
            href={getReportDownloadUrl(report.id)}
            className="text-sm font-medium text-primary-600 hover:text-primary-500"
          >
            Download
          </a>
        ) : report.status === 'failed' ? (
          <span className="text-sm text-red-500">{report.errorMessage}</span>
        ) : (
          <span className="text-sm text-gray-400">Processing...</span>
        )}
      </td>
    </tr>
  );
}
