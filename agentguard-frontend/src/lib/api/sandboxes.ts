import type { Incident, PaginatedResponse } from '@/types';
import type {
  SandboxAuditLogEntry,
  SandboxData,
  SandboxExecutionData,
  SandboxFilters,
  SandboxStats,
} from '@/types/sandbox';
import { apiFetch, buildQueryString } from './client';

// Sandbox CRUD

export async function listSandboxes(
  filters: SandboxFilters = {},
): Promise<PaginatedResponse<SandboxData>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<SandboxData>>(`/sandboxes${qs}`);
}

export async function getSandbox(id: string): Promise<SandboxData> {
  return apiFetch<SandboxData>(`/sandboxes/${id}`);
}

export async function createSandbox(data: {
  name: string;
  description?: string;
  agent_id?: string;
  image?: string;
  capabilities?: { type: string; target: string; expires_at?: string }[];
  resource_limits?: {
    cpu_shares?: number;
    memory_mb?: number;
    max_tokens?: number;
    timeout_seconds?: number;
  };
  network_policy?: {
    allowed_hosts?: string[];
    allowed_ports?: number[];
    deny_all_egress?: boolean;
  };
  environment?: Record<string, string>;
}): Promise<SandboxData> {
  return apiFetch<SandboxData>('/sandboxes', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateSandbox(
  id: string,
  data: Record<string, unknown>,
): Promise<SandboxData> {
  return apiFetch<SandboxData>(`/sandboxes/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteSandbox(id: string): Promise<void> {
  await apiFetch(`/sandboxes/${id}`, { method: 'DELETE' });
}

// Capabilities

export async function setCapabilities(
  sandboxId: string,
  capabilities: { type: string; target: string; expires_at?: string }[],
): Promise<SandboxData> {
  return apiFetch<SandboxData>(`/sandboxes/${sandboxId}/capabilities`, {
    method: 'PUT',
    body: JSON.stringify(capabilities),
  });
}

export async function addCapability(
  sandboxId: string,
  capability: { type: string; target: string; expires_at?: string },
): Promise<SandboxData> {
  return apiFetch<SandboxData>(`/sandboxes/${sandboxId}/capabilities`, {
    method: 'POST',
    body: JSON.stringify(capability),
  });
}

export async function removeCapability(
  sandboxId: string,
  index: number,
): Promise<SandboxData> {
  return apiFetch<SandboxData>(`/sandboxes/${sandboxId}/capabilities/${index}`, {
    method: 'DELETE',
  });
}

// Executions

export async function startExecution(
  sandboxId: string,
  trigger: string = 'api',
): Promise<SandboxExecutionData> {
  return apiFetch<SandboxExecutionData>(`/sandboxes/${sandboxId}/execute`, {
    method: 'POST',
    body: JSON.stringify({ trigger }),
  });
}

export async function listExecutions(
  sandboxId: string,
  params: { status?: string; skip?: number; limit?: number } = {},
): Promise<PaginatedResponse<SandboxExecutionData>> {
  const qs = buildQueryString(params as Record<string, unknown>);
  return apiFetch<PaginatedResponse<SandboxExecutionData>>(
    `/sandboxes/${sandboxId}/executions${qs}`,
  );
}

export async function getExecution(
  executionId: string,
): Promise<SandboxExecutionData> {
  return apiFetch<SandboxExecutionData>(`/sandboxes/executions/${executionId}`);
}

export async function stopExecution(
  executionId: string,
): Promise<SandboxExecutionData> {
  return apiFetch<SandboxExecutionData>(
    `/sandboxes/executions/${executionId}/stop`,
    { method: 'POST' },
  );
}

export async function terminateExecution(
  executionId: string,
): Promise<SandboxExecutionData> {
  return apiFetch<SandboxExecutionData>(
    `/sandboxes/executions/${executionId}/terminate`,
    { method: 'POST' },
  );
}

// Audit Logs

export async function getExecutionAuditLogs(
  executionId: string,
  params: { actionType?: string; skip?: number; limit?: number } = {},
): Promise<PaginatedResponse<SandboxAuditLogEntry>> {
  const qs = buildQueryString(params as Record<string, unknown>);
  return apiFetch<PaginatedResponse<SandboxAuditLogEntry>>(
    `/sandboxes/executions/${executionId}/audit${qs}`,
  );
}

export async function getSandboxAuditLogs(
  sandboxId: string,
  params: { actionType?: string; skip?: number; limit?: number } = {},
): Promise<PaginatedResponse<SandboxAuditLogEntry>> {
  const qs = buildQueryString(params as Record<string, unknown>);
  return apiFetch<PaginatedResponse<SandboxAuditLogEntry>>(
    `/sandboxes/${sandboxId}/audit${qs}`,
  );
}

// Execution → Incidents

export async function getExecutionIncidents(
  executionId: string,
  params: { skip?: number; limit?: number } = {},
): Promise<PaginatedResponse<Incident>> {
  const qs = buildQueryString(params as Record<string, unknown>);
  return apiFetch<PaginatedResponse<Incident>>(
    `/sandboxes/executions/${executionId}/incidents${qs}`,
  );
}

// Templates

export interface SandboxTemplate {
  id: string;
  name: string;
  description: string;
  image: string;
  capabilities: { type: string; target: string }[];
  resourceLimits: { cpu_shares: number; memory_mb: number; max_tokens: number; timeout_seconds: number };
  networkPolicy: { allowed_hosts: string[]; allowed_ports: number[]; deny_all_egress: boolean };
}

export async function listTemplates(): Promise<SandboxTemplate[]> {
  return apiFetch<SandboxTemplate[]>('/sandboxes/templates');
}

// Clone

export async function cloneSandbox(
  sandboxId: string,
  name: string,
): Promise<SandboxData> {
  return apiFetch<SandboxData>(`/sandboxes/${sandboxId}/clone`, {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

// Audit Export & Verify

export async function exportAuditLogs(
  sandboxId: string,
  format: 'json' | 'csv' = 'json',
): Promise<Blob> {
  const res = await fetch(`/api/v1/sandboxes/${sandboxId}/audit/export?format=${format}`, {
    headers: {
      Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('accessToken') ?? '' : ''}`,
    },
  });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  return res.blob();
}

export interface ChainVerification {
  valid: boolean;
  totalEntries: number;
  brokenAt: number | null;
  message: string;
}

export async function verifyAuditChain(
  sandboxId: string,
): Promise<ChainVerification> {
  return apiFetch<ChainVerification>(`/sandboxes/${sandboxId}/audit/verify`);
}

// Stats

export async function getSandboxStats(): Promise<SandboxStats> {
  return apiFetch<SandboxStats>('/sandboxes/stats');
}
