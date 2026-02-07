/**
 * Shadow AI discovery API client functions.
 */

import type { PaginatedResponse } from '@/types';
import { apiFetch, buildQueryString } from './client';

export interface ShadowAIDiscovery {
  id: string;
  provider: string;
  endpoint: string;
  department: string | null;
  sourceIp: string | null;
  riskLevel: string;
  status: string;
  requestCount: number;
  firstSeenAt: string;
  lastSeenAt: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface ShadowAIFilters {
  status?: string;
  provider?: string;
  riskLevel?: string;
  skip?: number;
  limit?: number;
}

export interface ShadowAISummary {
  totalDiscovered: number;
  monitoredCount: number;
  unmonitoredCount: number;
  blockedCount: number;
  totalUnmonitoredRequests: number;
  totalMonitoredRequests: number;
  coveragePct: number;
  byProvider: { provider: string; services: number; requests: number }[];
  byRisk: { riskLevel: string; count: number }[];
}

export async function listDiscoveries(
  filters: ShadowAIFilters = {},
): Promise<PaginatedResponse<ShadowAIDiscovery>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<ShadowAIDiscovery>>(`/shadow-ai${qs}`);
}

export async function getShadowAISummary(days: number = 30): Promise<ShadowAISummary> {
  return apiFetch<ShadowAISummary>(`/shadow-ai/summary?days=${days}`);
}

export async function updateDiscoveryStatus(
  id: string,
  status: string,
): Promise<ShadowAIDiscovery> {
  return apiFetch<ShadowAIDiscovery>(`/shadow-ai/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}
