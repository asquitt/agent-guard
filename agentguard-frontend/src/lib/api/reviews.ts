/**
 * Review queue API client functions.
 */

import type { PaginatedResponse } from '@/types';
import { apiFetch, buildQueryString } from './client';

export interface ReviewItem {
  id: string;
  incidentId: string | null;
  proxyRequestId: string | null;
  status: string;
  severity: string;
  category: string | null;
  title: string;
  description: string | null;
  reviewedBy: string | null;
  reviewedAt: string | null;
  decisionReason: string | null;
  escalationLevel: number;
  escalationDeadline: string | null;
  context: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface ReviewFilters {
  status?: string;
  severity?: string;
  skip?: number;
  limit?: number;
}

export interface ReviewStats {
  pending: number;
  approved: number;
  rejected: number;
  escalated: number;
  expired: number;
  avgReviewTimeMinutes: number | null;
}

export async function listReviews(
  filters: ReviewFilters = {},
): Promise<PaginatedResponse<ReviewItem>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<ReviewItem>>(`/reviews${qs}`);
}

export async function getReviewStats(days: number = 30): Promise<ReviewStats> {
  return apiFetch<ReviewStats>(`/reviews/stats?days=${days}`);
}

export async function decideReview(
  itemId: string,
  decision: 'approved' | 'rejected',
  reason?: string,
): Promise<ReviewItem> {
  return apiFetch<ReviewItem>(`/reviews/${itemId}/decide`, {
    method: 'POST',
    body: JSON.stringify({ decision, reason }),
  });
}

export async function escalateReview(itemId: string): Promise<ReviewItem> {
  return apiFetch<ReviewItem>(`/reviews/${itemId}/escalate`, {
    method: 'POST',
  });
}
