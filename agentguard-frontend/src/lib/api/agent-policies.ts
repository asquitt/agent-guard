/**
 * Agent behavior policies API client functions.
 */

import type { PaginatedResponse } from '@/types';
import { apiFetch, buildQueryString } from './client';

export interface TransactionLimit {
  currency: string;
  amount: number;
}

export interface CustomRule {
  rule: string;
  description: string;
}

export interface AgentPolicy {
  id: string;
  agentId: string;
  name: string;
  description: string | null;
  version: number;
  allowedTopics: string[];
  forbiddenTopics: string[];
  maxTransactionAmount: TransactionLimit | null;
  requiredDisclosures: string[];
  approvedDataSources: string[];
  approvedTools: string[];
  customRules: CustomRule[];
  createdAt: string;
  updatedAt: string;
}

export interface PolicyCreateData {
  name: string;
  description?: string;
  allowed_topics?: string[];
  forbidden_topics?: string[];
  max_transaction_amount?: TransactionLimit | null;
  required_disclosures?: string[];
  approved_data_sources?: string[];
  approved_tools?: string[];
  custom_rules?: CustomRule[];
}

export interface PolicyTemplate {
  id: string;
  name: string;
  description: string;
  policy: PolicyCreateData;
}

export async function listPolicies(
  agentId: string,
  filters: { skip?: number; limit?: number } = {},
): Promise<PaginatedResponse<AgentPolicy>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<AgentPolicy>>(
    `/agents/${agentId}/policies${qs}`,
  );
}

export async function getPolicy(
  agentId: string,
  policyId: string,
): Promise<AgentPolicy> {
  return apiFetch<AgentPolicy>(`/agents/${agentId}/policies/${policyId}`);
}

export async function createPolicy(
  agentId: string,
  data: PolicyCreateData,
): Promise<AgentPolicy> {
  return apiFetch<AgentPolicy>(`/agents/${agentId}/policies`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updatePolicy(
  agentId: string,
  policyId: string,
  data: Partial<PolicyCreateData>,
): Promise<AgentPolicy> {
  return apiFetch<AgentPolicy>(`/agents/${agentId}/policies/${policyId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deletePolicy(
  agentId: string,
  policyId: string,
): Promise<void> {
  await apiFetch(`/agents/${agentId}/policies/${policyId}`, {
    method: 'DELETE',
  });
}

export async function listPolicyTemplates(): Promise<PolicyTemplate[]> {
  return apiFetch<PolicyTemplate[]>('/agents/templates');
}
