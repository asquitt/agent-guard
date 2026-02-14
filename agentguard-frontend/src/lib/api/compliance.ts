/**
 * Compliance API client functions.
 */

import type {
  AuditLogEntry,
  AuditLogFilters,
  ChainVerification,
  ComplianceReport,
  ComplianceScores,
  PaginatedResponse,
} from '@/types';
import { apiFetch, buildQueryString } from './client';

export async function listAuditLogs(
  filters: AuditLogFilters = {},
): Promise<PaginatedResponse<AuditLogEntry>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<AuditLogEntry>>(`/compliance/audit-logs${qs}`);
}

export async function verifyAuditChain(): Promise<ChainVerification> {
  return apiFetch<ChainVerification>('/compliance/audit-logs/verify');
}

export async function createComplianceReport(data: {
  report_type: string;
  date_from: string;
  date_to: string;
}): Promise<ComplianceReport> {
  return apiFetch<ComplianceReport>('/compliance/reports', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function listComplianceReports(): Promise<PaginatedResponse<ComplianceReport>> {
  return apiFetch<PaginatedResponse<ComplianceReport>>('/compliance/reports');
}

export async function getFrameworkScores(days = 30): Promise<ComplianceScores> {
  return apiFetch<ComplianceScores>(`/compliance/frameworks/scores?days=${days}`);
}

export async function downloadReport(reportId: string): Promise<Blob> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
  const base = process.env.NEXT_PUBLIC_API_URL || '';
  const res = await fetch(`${base}/api/v1/compliance/reports/${reportId}/download`, {
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  });
  if (!res.ok) throw new Error(`Download failed: ${res.status}`);
  return res.blob();
}

export async function downloadCefExport(): Promise<Blob> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
  const base = process.env.NEXT_PUBLIC_API_URL || '';
  const res = await fetch(`${base}/api/v1/compliance/audit-logs/export/cef`, {
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  return res.blob();
}
