/**
 * Dashboard and analytics type definitions.
 */

import type { UUID } from './common';

// Dashboard
export interface IncidentCountByStatus {
  status: string;
  count: number;
}

export interface IncidentCountBySeverity {
  severity: string;
  count: number;
}

export interface RecentIncidentSummary {
  id: UUID;
  title: string;
  severity: string;
  status: string;
  category: string;
  createdAt: string;
}

export interface DashboardMetrics {
  totalIncidents: number;
  openIncidents: number;
  incidentsByStatus: IncidentCountByStatus[];
  incidentsBySeverity: IncidentCountBySeverity[];
  recentIncidents: RecentIncidentSummary[];
}

// Cost Analytics
export interface CostByModel {
  model: string;
  cost: number;
  requests: number;
  inputTokens: number;
  outputTokens: number;
}

export interface DailyCost {
  date: string;
  cost: number;
  requests: number;
  inputTokens: number;
  outputTokens: number;
}

export interface CostAnalytics {
  totalCost: number;
  totalRequests: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  costByModel: CostByModel[];
  dailyCosts: DailyCost[];
  periodDays: number;
}

// SLA Metrics
export interface ProviderSlaMetrics {
  provider: string;
  totalRequests: number;
  errorRate: number;
  p50LatencyMs: number | null;
  p95LatencyMs: number | null;
  p99LatencyMs: number | null;
}

export interface SlaMetrics {
  totalRequests: number;
  errorRate: number;
  p50LatencyMs: number | null;
  p95LatencyMs: number | null;
  p99LatencyMs: number | null;
  avgThroughputPerHour: number;
  uptimePct: number;
  byProvider: ProviderSlaMetrics[];
  periodDays: number;
}
