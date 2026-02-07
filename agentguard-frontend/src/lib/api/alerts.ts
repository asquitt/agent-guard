/**
 * Alerts API client functions.
 */

import type { Alert, AlertDestination, PaginatedResponse } from '@/types';
import { apiFetch } from './client';

export async function listDestinations(
  skip = 0,
  limit = 50,
): Promise<PaginatedResponse<AlertDestination>> {
  return apiFetch<PaginatedResponse<AlertDestination>>(
    `/alerts/destinations?skip=${skip}&limit=${limit}`,
  );
}

export async function createDestination(body: {
  name: string;
  destination_type: string;
  config?: Record<string, unknown>;
}): Promise<AlertDestination> {
  return apiFetch<AlertDestination>('/alerts/destinations', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function updateDestination(
  id: string,
  body: {
    name?: string;
    is_active?: boolean;
    config?: Record<string, unknown>;
  },
): Promise<AlertDestination> {
  return apiFetch<AlertDestination>(`/alerts/destinations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export async function deleteDestination(id: string): Promise<void> {
  await apiFetch<void>(`/alerts/destinations/${id}`, { method: 'DELETE' });
}

export async function testDestination(
  id: string,
): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>(
    `/alerts/destinations/${id}/test`,
    { method: 'POST' },
  );
}

export async function listAlerts(
  skip = 0,
  limit = 50,
): Promise<PaginatedResponse<Alert>> {
  return apiFetch<PaginatedResponse<Alert>>(
    `/alerts/?skip=${skip}&limit=${limit}`,
  );
}
