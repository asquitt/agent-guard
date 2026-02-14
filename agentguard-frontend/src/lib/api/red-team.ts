/**
 * Adversarial red teaming API client functions.
 */

import type { PaginatedResponse } from '@/types';
import { apiFetch, buildQueryString } from './client';

export interface RedTeamFinding {
  id: string;
  testCategory: string;
  testName: string;
  passed: boolean;
  severity: string;
  attackPrompt: string | null;
  modelResponse: string | null;
  explanation: string | null;
  createdAt: string;
}

export interface RedTeamRun {
  id: string;
  name: string;
  status: string;
  testCategories: string[];
  totalTests: number;
  passedTests: number;
  failedTests: number;
  resilienceScore: number | null;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
}

export interface RedTeamRunDetail extends RedTeamRun {
  findings: RedTeamFinding[];
}

export interface RedTeamRunFilters {
  status?: string;
  skip?: number;
  limit?: number;
}

export interface RedTeamStats {
  totalRuns: number;
  completedRuns: number;
  avgResilience: number;
  totalFindings: number;
  byCategory: { category: string; total: number; failures: number }[];
  resilienceTrend: { name: string; score: number; date: string | null }[];
}

export interface RedTeamRunCreate {
  name: string;
  endpointId?: string;
  testCategories: string[];
}

export async function listRedTeamRuns(
  filters: RedTeamRunFilters = {},
): Promise<PaginatedResponse<RedTeamRun>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<RedTeamRun>>(`/red-team${qs}`);
}

export async function getRedTeamRun(id: string): Promise<RedTeamRunDetail> {
  return apiFetch<RedTeamRunDetail>(`/red-team/${id}`);
}

export async function getRedTeamStats(days: number = 90): Promise<RedTeamStats> {
  return apiFetch<RedTeamStats>(`/red-team/stats?days=${days}`);
}

export async function createRedTeamRun(data: RedTeamRunCreate): Promise<RedTeamRun> {
  return apiFetch<RedTeamRun>('/red-team', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export interface OwaspMapping {
  [key: string]: { name: string; categories: string[] };
}

export interface CategoriesResponse {
  categories: string[];
  owasp_mapping: OwaspMapping;
}

export interface MultiTurnSequenceInfo {
  steps: number;
  description: string;
}

export interface MutationVariant {
  name: string;
  prompt: string;
  strategy: string;
}

export async function getTestCategories(): Promise<CategoriesResponse> {
  return apiFetch<CategoriesResponse>('/red-team/categories');
}

export async function getMultiTurnSequences(): Promise<{ sequences: Record<string, MultiTurnSequenceInfo> }> {
  return apiFetch<{ sequences: Record<string, MultiTurnSequenceInfo> }>('/red-team/multi-turn/sequences');
}

export async function getMutationStrategies(): Promise<{ strategies: string[] }> {
  return apiFetch<{ strategies: string[] }>('/red-team/mutations/strategies');
}

export async function generateMutations(
  prompt: string,
  strategies?: string[],
): Promise<{ original: string; mutations: MutationVariant[] }> {
  return apiFetch<{ original: string; mutations: MutationVariant[] }>('/red-team/mutations/generate', {
    method: 'POST',
    body: JSON.stringify({ prompt, strategies }),
  });
}
