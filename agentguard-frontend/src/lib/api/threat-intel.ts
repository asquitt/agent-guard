/**
 * Threat intelligence feed API client functions.
 */

import type { PaginatedResponse } from '@/types';
import { apiFetch, buildQueryString } from './client';

export interface ThreatIndicator {
  id: string;
  indicatorType: string;
  name: string;
  description: string | null;
  pattern: string | null;
  severity: string;
  confidence: number;
  source: string;
  hitCount: number;
  lastSeenAt: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ThreatIndicatorFilters {
  indicatorType?: string;
  severity?: string;
  source?: string;
  isActive?: boolean;
  skip?: number;
  limit?: number;
}

export interface ThreatSummary {
  totalIndicators: number;
  activeIndicators: number;
  totalHits: number;
  byType: { type: string; count: number }[];
  bySeverity: { severity: string; count: number }[];
  topIndicators: { name: string; type: string; hits: number; severity: string }[];
  recentIndicators: ThreatIndicator[];
}

export interface IndicatorCreateData {
  indicatorType: string;
  name: string;
  description?: string;
  pattern?: string;
  severity?: string;
  confidence?: number;
}

export async function listIndicators(
  filters: ThreatIndicatorFilters = {},
): Promise<PaginatedResponse<ThreatIndicator>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<ThreatIndicator>>(`/threat-intel${qs}`);
}

export async function getThreatSummary(days: number = 30): Promise<ThreatSummary> {
  return apiFetch<ThreatSummary>(`/threat-intel/summary?days=${days}`);
}

export async function createIndicator(data: IndicatorCreateData): Promise<ThreatIndicator> {
  return apiFetch<ThreatIndicator>('/threat-intel', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateIndicator(
  id: string,
  data: Partial<{ isActive: boolean; pattern: string; severity: string; confidence: number }>,
): Promise<ThreatIndicator> {
  return apiFetch<ThreatIndicator>(`/threat-intel/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function seedPlatformIndicators(): Promise<{ seeded: number }> {
  return apiFetch<{ seeded: number }>('/threat-intel/seed', { method: 'POST' });
}

export async function getIndicatorTypes(): Promise<{ types: string[] }> {
  return apiFetch<{ types: string[] }>('/threat-intel/types');
}
