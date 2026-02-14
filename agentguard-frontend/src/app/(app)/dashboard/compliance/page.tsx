'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  listAuditLogs,
  verifyAuditChain,
  createComplianceReport,
  listComplianceReports,
  downloadReport,
  downloadCefExport,
} from '@/lib/api';
import { ComplianceScoreboard } from '@/components/dashboard/ComplianceScoreboard';
import type { AuditLogEntry, AuditLogFilters, ComplianceReport } from '@/types';
import { REPORT_STATUS_COLORS, VERIFICATION_COLORS } from '@/lib/constants';

const PAGE_SIZE = 20;

const REPORT_TYPES = [
  { value: 'access_audit', label: 'Access Audit', group: 'General' },
  { value: 'incident_summary', label: 'Incident Summary', group: 'General' },
  { value: 'detection_efficacy', label: 'Detection Efficacy', group: 'General' },
  { value: 'configuration_changes', label: 'Configuration Changes', group: 'General' },
  { value: 'sox_governance', label: 'SOX Governance', group: 'Regulatory' },
  { value: 'pci_dss_security', label: 'PCI-DSS Security', group: 'Regulatory' },
  { value: 'ffiec_risk', label: 'FFIEC Risk Assessment', group: 'Regulatory' },
  { value: 'nydfs_500_cyber', label: 'NYDFS Part 500', group: 'Regulatory' },
  { value: 'dora_ict', label: 'DORA ICT Risk', group: 'Regulatory' },
  { value: 'eu_ai_act', label: 'EU AI Act', group: 'Regulatory' },
];

export default function CompliancePage() {
  const [tab, setTab] = useState<'audit' | 'reports'>('audit');

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Compliance</h1>
        <p className="text-sm text-muted-foreground">Framework scoreboard, audit logs, and compliance reports</p>
      </div>

      <ComplianceScoreboard />

      <div role="tablist" aria-label="Compliance sections" className="mb-6 flex gap-1 rounded-lg bg-muted p-1">
        <button
          role="tab"
          aria-selected={tab === 'audit'}
          aria-controls="panel-audit"
          onClick={() => setTab('audit')}
          className={clsx(
            'rounded-md px-4 py-2 text-sm font-medium transition-colors',
            tab === 'audit' ? 'bg-card text-foreground shadow-sm shadow-black/10' : 'text-muted-foreground hover:text-foreground',
          )}
        >
          Audit Log
        </button>
        <button
          role="tab"
          aria-selected={tab === 'reports'}
          aria-controls="panel-reports"
          onClick={() => setTab('reports')}
          className={clsx(
            'rounded-md px-4 py-2 text-sm font-medium transition-colors',
            tab === 'reports' ? 'bg-card text-foreground shadow-sm shadow-black/10' : 'text-muted-foreground hover:text-foreground',
          )}
        >
          Reports
        </button>
      </div>

      <div role="tabpanel" id={`panel-${tab}`}>
        {tab === 'audit' ? <AuditLogTab /> : <ReportsTab />}
      </div>
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
          className="rounded-lg border border-border px-3 py-2 text-sm"
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
          className="rounded-lg border border-border px-3 py-2 text-sm"
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
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/100 disabled:opacity-50"
        >
          {verifyMutation.isPending ? 'Verifying...' : 'Verify Integrity'}
        </button>
        <button
          onClick={async () => {
            const blob = await downloadCefExport();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'audit_logs.cef';
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50"
        >
          Export CEF
        </button>
        {verifyMutation.data && (
          <span
            className={clsx(
              'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
              verifyMutation.data.valid
                ? VERIFICATION_COLORS.valid
                : VERIFICATION_COLORS.invalid,
            )}
          >
            {verifyMutation.data.valid
              ? `Valid (${verifyMutation.data.checked} entries)`
              : `Broken at ${verifyMutation.data.brokenAt}`}
          </span>
        )}
      </div>

      <div className="rounded-xl border border-border bg-card">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center">
              <p className="text-sm font-semibold text-foreground">No audit logs found</p>
              <p className="mt-1 text-xs text-muted-foreground">Adjust your filters or check back after activity.</p>
            </div>
        ) : (
          <>
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Resource</th>
                  <th className="px-4 py-3">IP Address</th>
                  <th className="px-4 py-3">User ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {logs.map((log) => (
                  <AuditLogRow key={log.id} log={log} />
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <nav aria-label="Audit log pagination" className="flex items-center justify-between border-t border-border px-4 py-3">
                <button
                  disabled={page === 0}
                  aria-label="Go to previous page"
                  onClick={() => setFilters((f) => ({ ...f, skip: Math.max(0, (f.skip ?? 0) - PAGE_SIZE) }))}
                  className="rounded-lg px-3 py-1.5 text-sm text-foreground hover:bg-muted disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-sm text-muted-foreground" aria-current="page">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  disabled={page >= totalPages - 1}
                  aria-label="Go to next page"
                  onClick={() => setFilters((f) => ({ ...f, skip: (f.skip ?? 0) + PAGE_SIZE }))}
                  className="rounded-lg px-3 py-1.5 text-sm text-foreground hover:bg-muted disabled:opacity-50"
                >
                  Next
                </button>
              </nav>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function AuditLogRow({ log }: { log: AuditLogEntry }) {
  return (
    <tr className="hover:bg-muted/50">
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {new Date(log.createdAt).toLocaleString()}
      </td>
      <td className="px-4 py-3 text-sm font-medium text-foreground">{log.action}</td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {log.resourceType}
        {log.resourceId && <span className="ml-1 text-muted-foreground/60">{log.resourceId.slice(0, 8)}...</span>}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">{log.ipAddress ?? '-'}</td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
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
      <div className="mb-6 rounded-xl border border-border bg-card p-6">
        <h3 className="mb-4 text-sm font-medium text-foreground">Generate Report</h3>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="rounded-lg border border-border px-3 py-2 text-sm"
            >
              <optgroup label="General">
                {REPORT_TYPES.filter((rt) => rt.group === 'General').map((rt) => (
                  <option key={rt.value} value={rt.value}>{rt.label}</option>
                ))}
              </optgroup>
              <optgroup label="Regulatory Frameworks">
                {REPORT_TYPES.filter((rt) => rt.group === 'Regulatory').map((rt) => (
                  <option key={rt.value} value={rt.value}>{rt.label}</option>
                ))}
              </optgroup>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-lg border border-border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-lg border border-border px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={handleGenerate}
            disabled={!dateFrom || !dateTo || createMutation.isPending}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/100 disabled:opacity-50"
          >
            {createMutation.isPending ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : reports.length === 0 ? (
          <div className="py-16 text-center">
              <p className="text-sm font-semibold text-foreground">No reports generated</p>
              <p className="mt-1 text-xs text-muted-foreground">Use the form above to generate your first compliance report.</p>
            </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Period</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
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
    <tr className="hover:bg-muted/50">
      <td className="px-4 py-3 text-sm font-medium text-foreground">{typeLabel}</td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {new Date(report.dateFrom).toLocaleDateString()} - {new Date(report.dateTo).toLocaleDateString()}
      </td>
      <td className="px-4 py-3">
        <span
          className={clsx(
            'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
            REPORT_STATUS_COLORS[report.status] ?? 'bg-muted text-muted-foreground',
          )}
        >
          {report.status}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {report.fileSizeBytes ? `${(report.fileSizeBytes / 1024).toFixed(1)} KB` : '-'}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {new Date(report.createdAt).toLocaleString()}
      </td>
      <td className="px-4 py-3">
        {report.status === 'completed' ? (
          <button
            onClick={async () => {
              const blob = await downloadReport(report.id);
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `${report.reportType}_${report.id}.csv`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="text-sm font-medium text-primary hover:text-primary"
          >
            Download
          </button>
        ) : report.status === 'failed' ? (
          <span className="text-sm text-red-500">{report.errorMessage}</span>
        ) : (
          <span className="text-sm text-muted-foreground/60">Processing...</span>
        )}
      </td>
    </tr>
  );
}
