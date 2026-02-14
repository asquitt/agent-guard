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

export interface TimeSeriesBucket {
  bucket: string;
  incidents: number;
  requests: number;
  avgLatencyMs: number | null;
  totalCostUsd: number;
  totalTokens: number;
  detections: number;
  errorCount: number;
}

export interface TimeSeriesData {
  buckets: TimeSeriesBucket[];
  granularity: string;
  periodDays: number;
}

export async function getTimeSeries(
  days: number = 7,
  granularity: string = 'auto',
): Promise<TimeSeriesData> {
  return apiFetch<TimeSeriesData>(
    `/dashboard/time-series?days=${days}&granularity=${granularity}`,
  );
}

// --- Risk Score ---

export interface CategoryRisk {
  category: string;
  score: number;
  incidentCount: number;
  criticalCount: number;
  highCount: number;
  openCount: number;
}

export interface RiskTrendPoint {
  date: string;
  score: number;
}

export interface RiskScoreData {
  overallScore: number;
  grade: string;
  trendDirection: 'improving' | 'stable' | 'degrading';
  categories: CategoryRisk[];
  trend: RiskTrendPoint[];
  totalIncidents: number;
  openIncidents: number;
  criticalOpen: number;
  periodDays: number;
}

export async function getRiskScore(days: number = 30): Promise<RiskScoreData> {
  return apiFetch<RiskScoreData>(`/dashboard/risk-score?days=${days}`);
}
