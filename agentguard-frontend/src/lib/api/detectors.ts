/**
 * Detectors API client functions.
 */

import type { Detector, PaginatedResponse } from '@/types';
import { apiFetch } from './client';

export async function listDetectors(
  skip = 0,
  limit = 50,
): Promise<PaginatedResponse<Detector>> {
  return apiFetch<PaginatedResponse<Detector>>(
    `/detectors/?skip=${skip}&limit=${limit}`,
  );
}

export async function getDetector(id: string): Promise<Detector> {
  return apiFetch<Detector>(`/detectors/${id}`);
}

export async function createDetector(body: {
  name: string;
  category: string;
  action_mode?: string;
  config?: Record<string, unknown>;
}): Promise<Detector> {
  return apiFetch<Detector>('/detectors/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function updateDetector(
  id: string,
  body: {
    name?: string;
    is_active?: boolean;
    action_mode?: string;
    config?: Record<string, unknown>;
  },
): Promise<Detector> {
  return apiFetch<Detector>(`/detectors/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export async function deleteDetector(id: string): Promise<void> {
  await apiFetch<void>(`/detectors/${id}`, { method: 'DELETE' });
}
