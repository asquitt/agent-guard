/**
 * Incidents API client functions.
 */

import type {
  Incident,
  IncidentAction,
  IncidentDetail,
  IncidentFilters,
  PaginatedResponse,
} from '@/types';
import { apiFetch, buildQueryString } from './client';

export async function listIncidents(
  filters: IncidentFilters = {},
): Promise<PaginatedResponse<Incident>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<Incident>>(`/incidents/${qs}`);
}

export async function getIncident(id: string): Promise<IncidentDetail> {
  return apiFetch<IncidentDetail>(`/incidents/${id}`);
}

export async function updateIncidentStatus(
  id: string,
  status: string,
): Promise<Incident> {
  return apiFetch<Incident>(`/incidents/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

export async function addIncidentAction(
  incidentId: string,
  actionType: string,
  details?: Record<string, unknown>,
): Promise<IncidentAction> {
  return apiFetch<IncidentAction>(`/incidents/${incidentId}/actions`, {
    method: 'POST',
    body: JSON.stringify({ action_type: actionType, details }),
  });
}

export async function bulkUpdateStatus(
  incidentIds: string[],
  status: string,
): Promise<{ updated: number }> {
  return apiFetch<{ updated: number }>('/incidents/bulk-update', {
    method: 'POST',
    body: JSON.stringify({ incident_ids: incidentIds, status }),
  });
}
