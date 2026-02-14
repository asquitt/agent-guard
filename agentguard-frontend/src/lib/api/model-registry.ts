/**
 * AI Model Registry API client.
 */

import { apiFetch, buildQueryString } from './client';

export interface AIModel {
  id: string;
  modelName: string;
  modelVersion: string;
  provider: string;
  modelType: string;
  licenseType: string | null;
  modelHash: string | null;
  repositoryUrl: string | null;
  modelCardUrl: string | null;
  releaseDate: string | null;
  parameterCount: string | null;
  contextWindow: number | null;
  riskLevel: string;
  riskFactors: string[];
  complianceFrameworks: string[];
  knownLimitations: string[];
  securityIssues: string[];
  piiHandling: string;
  trainingDataSources: string[];
  trainingCutoff: string | null;
  modelDependencies: string[];
  capabilities: string[];
  approvalStatus: string;
  approvalNotes: string | null;
  ownerEmail: string | null;
  isDeprecated: boolean;
  totalRequests: number;
  totalIncidents: number;
  lastUsedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AIModelListResponse {
  items: AIModel[];
  total: number;
}

export interface ModelSummary {
  totalModels: number;
  approved: number;
  pending: number;
  deprecated: number;
  byRiskLevel: Record<string, number>;
  byProvider: Record<string, number>;
}

export interface AIModelCreate {
  model_name: string;
  model_version?: string;
  provider: string;
  model_type?: string;
  license_type?: string;
  risk_level?: string;
  risk_factors?: string[];
  compliance_frameworks?: string[];
  capabilities?: string[];
  pii_handling?: string;
  owner_email?: string;
  parameter_count?: string;
  context_window?: number;
  model_card_url?: string;
  training_cutoff?: string;
}

export interface AIModelFilters {
  provider?: string;
  riskLevel?: string;
  approvalStatus?: string;
  modelType?: string;
  q?: string;
  skip?: number;
  limit?: number;
}

export async function listModels(filters: AIModelFilters = {}): Promise<AIModelListResponse> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<AIModelListResponse>(`/model-registry${qs ? `?${qs}` : ''}`);
}

export async function getModel(id: string): Promise<AIModel> {
  return apiFetch<AIModel>(`/model-registry/${id}`);
}

export async function getModelSummary(): Promise<ModelSummary> {
  return apiFetch<ModelSummary>('/model-registry/summary');
}

export async function createModel(data: AIModelCreate): Promise<AIModel> {
  return apiFetch<AIModel>('/model-registry', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateModel(
  id: string,
  data: Partial<AIModelCreate & { approval_status?: string; is_deprecated?: boolean }>,
): Promise<AIModel> {
  return apiFetch<AIModel>(`/model-registry/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteModel(id: string): Promise<void> {
  await apiFetch(`/model-registry/${id}`, { method: 'DELETE' });
}
