/**
 * Data retention API client functions.
 */

import type {
  DataArchive,
  PaginatedResponse,
  RetentionPolicy,
  RetentionPolicyUpdate,
} from '@/types';
import { apiFetch, buildQueryString } from './client';

export async function getRetentionPolicy(): Promise<RetentionPolicy> {
  return apiFetch<RetentionPolicy>('/retention/policy');
}

export async function updateRetentionPolicy(
  data: RetentionPolicyUpdate,
): Promise<RetentionPolicy> {
  return apiFetch<RetentionPolicy>('/retention/policy', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function listArchives(
  params: { tableName?: string; skip?: number; limit?: number } = {},
): Promise<PaginatedResponse<DataArchive>> {
  const qs = buildQueryString(params as Record<string, unknown>);
  return apiFetch<PaginatedResponse<DataArchive>>(`/retention/archives${qs}`);
}

export async function retrieveArchive(
  archiveId: string,
): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>(
    `/retention/archives/${archiveId}/retrieve`,
    { method: 'POST' },
  );
}
