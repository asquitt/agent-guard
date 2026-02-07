/**
 * Dashboard API client functions.
 */

import type { DashboardMetrics } from '@/types';
import { apiFetch } from './client';

export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  return apiFetch<DashboardMetrics>('/dashboard/metrics');
}
