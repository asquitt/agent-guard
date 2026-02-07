/**
 * API Keys API client functions.
 */

import type { ApiKey, ApiKeyCreateResponse, PaginatedResponse } from '@/types';
import { apiFetch } from './client';

export async function listApiKeys(
  skip = 0,
  limit = 50,
): Promise<PaginatedResponse<ApiKey>> {
  return apiFetch<PaginatedResponse<ApiKey>>(
    `/api-keys/?skip=${skip}&limit=${limit}`,
  );
}

export async function createApiKey(body: {
  name: string;
  scopes?: string[];
}): Promise<ApiKeyCreateResponse> {
  return apiFetch<ApiKeyCreateResponse>('/api-keys/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function revokeApiKey(id: string): Promise<ApiKey> {
  return apiFetch<ApiKey>(`/api-keys/${id}`, { method: 'DELETE' });
}
