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
