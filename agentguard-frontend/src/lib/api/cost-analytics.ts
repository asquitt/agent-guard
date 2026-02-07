/**
 * Cost analytics API client.
 */

import type { CostAnalytics } from '@/types';
import { apiFetch } from './client';

export async function getCostAnalytics(days = 30): Promise<CostAnalytics> {
  return apiFetch<CostAnalytics>(`/dashboard/cost-analytics?days=${days}`);
}
