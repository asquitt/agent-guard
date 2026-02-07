/**
 * Agent registry API client functions.
 */

import type { PaginatedResponse } from '@/types';
import { apiFetch, buildQueryString } from './client';

export interface AgentData {
  id: string;
  name: string;
  description: string | null;
  owner: string | null;
  riskTier: string;
  status: string;
  provider: string | null;
  model: string | null;
  frameworks: string[];
  tags: string[];
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface AgentFilters {
  riskTier?: string;
  status?: string;
  q?: string;
  skip?: number;
  limit?: number;
}

export async function listAgents(
  filters: AgentFilters = {},
): Promise<PaginatedResponse<AgentData>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<AgentData>>(`/agents${qs}`);
}

export async function getAgent(id: string): Promise<AgentData> {
  return apiFetch<AgentData>(`/agents/${id}`);
}

export async function createAgent(data: {
  name: string;
  description?: string;
  owner?: string;
  risk_tier?: string;
  status?: string;
  provider?: string;
  model?: string;
  frameworks?: string[];
  tags?: string[];
}): Promise<AgentData> {
  return apiFetch<AgentData>('/agents', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateAgent(
  id: string,
  data: Record<string, unknown>,
): Promise<AgentData> {
  return apiFetch<AgentData>(`/agents/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteAgent(id: string): Promise<void> {
  await apiFetch(`/agents/${id}`, { method: 'DELETE' });
}
