/**
 * SIEM/SOAR integration API client functions.
 */

import { apiFetch, buildQueryString } from './client';

export interface SiemFormat {
  id: string;
  name: string;
  description: string;
}

export interface SiemDestination {
  id: string;
  name: string;
  url: string;
  format: string;
  eventTypes: string[];
  minSeverity: string;
  isActive: boolean;
  createdAt: string;
}

export interface SiemDestinationCreate {
  name: string;
  url: string;
  format: string;
  auth_header?: string;
  event_types?: string[];
  min_severity?: string;
}

export interface SiemDestinationUpdate {
  name?: string;
  url?: string;
  format?: string;
  auth_header?: string;
  event_types?: string[];
  min_severity?: string;
  is_active?: boolean;
}

export interface SiemDestinationList {
  items: SiemDestination[];
  total: number;
}

export interface FormatPreview {
  format: string;
  output: string;
}

export async function listSiemFormats(): Promise<{ formats: SiemFormat[] }> {
  return apiFetch<{ formats: SiemFormat[] }>('/siem/formats');
}

export async function previewSiemFormat(format: string): Promise<FormatPreview> {
  return apiFetch<FormatPreview>(`/siem/preview?fmt=${encodeURIComponent(format)}`);
}

export async function listSiemDestinations(
  skip = 0,
  limit = 50,
): Promise<SiemDestinationList> {
  const qs = buildQueryString({ skip, limit });
  return apiFetch<SiemDestinationList>(`/siem${qs}`);
}

export async function createSiemDestination(
  data: SiemDestinationCreate,
): Promise<SiemDestination> {
  return apiFetch<SiemDestination>('/siem', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateSiemDestination(
  id: string,
  data: SiemDestinationUpdate,
): Promise<SiemDestination> {
  return apiFetch<SiemDestination>(`/siem/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteSiemDestination(id: string): Promise<void> {
  await apiFetch<void>(`/siem/${id}`, { method: 'DELETE' });
}
