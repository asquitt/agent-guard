/**
 * TypeScript type definitions for AgentGuard.
 */

// Common types
export type UUID = string;

// Auth
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthUser {
  id: UUID;
  email: string;
  name: string;
  role: string;
  organizationId: UUID;
  isActive: boolean;
  createdAt: string;
}

export interface AuthOrganization {
  id: UUID;
  name: string;
  slug: string;
  planTier: string;
  createdAt: string;
}

export interface MeResponse {
  user: AuthUser;
  organization: AuthOrganization;
}

// Incidents
export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type IncidentStatus = 'open' | 'acknowledged' | 'resolved' | 'dismissed';
export type IncidentCategory = 'hallucination' | 'pii_leak' | 'compliance' | 'cost_anomaly' | 'loop';

export interface Incident {
  id: UUID;
  severity: string;
  category: string;
  title: string;
  description: string | null;
  status: string;
  actionTaken: string | null;
  proxyRequestId: UUID | null;
  detectorId: UUID | null;
  resolvedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface IncidentAction {
  id: UUID;
  actionType: string;
  userId: UUID | null;
  details: Record<string, unknown>;
  createdAt: string;
}

export interface IncidentDetail extends Incident {
  actions: IncidentAction[];
}

export interface IncidentFilters {
  status?: string;
  severity?: string;
  category?: string;
  detectorId?: string;
  q?: string;
  dateFrom?: string;
  dateTo?: string;
  skip?: number;
  limit?: number;
}

// Detectors
export type DetectorType = 'hallucination' | 'pii_leak' | 'compliance' | 'cost_anomaly' | 'loop';

export interface Detector {
  id: UUID;
  organizationId: UUID;
  name: string;
  type: DetectorType;
  enabled: boolean;
  config: Record<string, unknown>;
  createdAt: string;
}

// Alerts
export type AlertDestinationType = 'slack' | 'pagerduty' | 'email' | 'webhook';

export interface AlertDestination {
  id: UUID;
  organizationId: UUID;
  name: string;
  type: AlertDestinationType;
  config: Record<string, unknown>;
  enabled: boolean;
  createdAt: string;
}

export interface Alert {
  id: UUID;
  incidentId: UUID;
  destinationId: UUID;
  status: 'pending' | 'sent' | 'failed';
  sentAt?: string;
  createdAt: string;
}

// Proxy
export interface ProxyEndpoint {
  id: UUID;
  organizationId: UUID;
  name: string;
  provider: 'openai' | 'anthropic' | 'custom';
  baseUrl: string;
  enabled: boolean;
  createdAt: string;
}

export interface ProxyRequest {
  id: UUID;
  organizationId: UUID;
  endpointId: UUID;
  model: string;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
  createdAt: string;
}

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

// Paginated response wrapper
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}
