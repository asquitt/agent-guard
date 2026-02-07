/**
 * Dashboard API client functions.
 */

import type { DashboardMetrics, DetectionEfficacy, SlaMetrics } from '@/types';
import { apiFetch } from './client';

export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  return apiFetch<DashboardMetrics>('/dashboard/metrics');
}

export async function getSlaMetrics(days: number = 30): Promise<SlaMetrics> {
  return apiFetch<SlaMetrics>(`/dashboard/sla-metrics?days=${days}`);
}

export async function getDetectionEfficacy(days: number = 30): Promise<DetectionEfficacy> {
  return apiFetch<DetectionEfficacy>(`/dashboard/detection-efficacy?days=${days}`);
}

export interface ProviderPerformance {
  model: string;
  totalRequests: number;
  errorRate: number;
  avgLatencyMs: number | null;
  p95LatencyMs: number | null;
  totalCostUsd: number;
  avgCostPerRequest: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  incidentCount: number;
  incidentRate: number;
}

export interface ProviderComparisonData {
  providers: ProviderPerformance[];
  periodDays: number;
}

export async function getProviderComparison(days: number = 30): Promise<ProviderComparisonData> {
  return apiFetch<ProviderComparisonData>(`/dashboard/provider-comparison?days=${days}`);
}
