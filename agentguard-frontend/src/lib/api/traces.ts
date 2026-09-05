/**
 * Trace (proxy request) API client.
 */

import { apiFetch, buildQueryString } from './client';

export interface TraceListItem {
  id: string;
  method: string;
  path: string;
  model: string | null;
  statusCode: number | null;
  latencyMs: number | null;
  inputTokens: number | null;
  outputTokens: number | null;
  costUsd: number | null;
  incidentCount: number;
  createdAt: string;
}

export interface TraceIncident {
  id: string;
  severity: string;
  category: string;
  title: string;
  status: string;
  actionTaken: string | null;
  createdAt: string;
}

export interface TraceDetail extends TraceListItem {
  requestBody: string | null;
  responseBody: string | null;
  incidents: TraceIncident[];
  updatedAt: string;
}

export interface TraceListResponse {
  items: TraceListItem[];
  total: number;
}

export interface TraceFilters {
  model?: string;
  statusCode?: number;
  hasIncidents?: boolean;
  q?: string;
  skip?: number;
  limit?: number;
}

export async function listTraces(filters: TraceFilters = {}): Promise<TraceListResponse> {
  const qs = buildQueryString(filters as Record<string, string | number | boolean | undefined>);
  return apiFetch<TraceListResponse>(`/traces${qs}`);
}

export async function getTrace(traceId: string): Promise<TraceDetail> {
  return apiFetch<TraceDetail>(`/traces/${traceId}`);
}
