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
  settings: Record<string, unknown>;
  createdAt: string;
}

export interface MeResponse {
  user: AuthUser;
  organization: AuthOrganization;
}

// Incidents
export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type IncidentStatus = 'open' | 'acknowledged' | 'resolved' | 'dismissed';
export type IncidentCategory = 'hallucination' | 'pii_leak' | 'compliance' | 'cost_anomaly' | 'loop' | 'prompt_injection' | 'prompt_extraction' | 'toxicity' | 'tool_call' | 'mcp_security';

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
  sandboxExecutionId: UUID | null;
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
export type DetectorCategory = 'hallucination' | 'pii_leak' | 'compliance' | 'cost_anomaly' | 'loop' | 'prompt_injection' | 'prompt_extraction' | 'toxicity' | 'tool_call' | 'mcp_security';

export interface DetectorRule {
  id: UUID;
  name: string;
  ruleType: string;
  parameters: Record<string, unknown>;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Detector {
  id: UUID;
  name: string;
  category: string;
  isActive: boolean;
  actionMode: string;
  config: Record<string, unknown>;
  rules: DetectorRule[];
  createdAt: string;
  updatedAt: string;
}

// API Keys
export interface ApiKey {
  id: UUID;
  prefix: string;
  name: string;
  scopes: string[];
  isActive: boolean;
  lastUsedAt: string | null;
  expiresAt: string | null;
  createdAt: string;
}

export interface ApiKeyCreateResponse extends ApiKey {
  key: string;
}

// Alerts
export type AlertDestinationType = 'slack' | 'pagerduty' | 'email' | 'webhook';

export interface AlertDestination {
  id: UUID;
  name: string;
  destinationType: string;
  config: Record<string, unknown>;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Alert {
  id: UUID;
  incidentId: UUID;
  destinationId: UUID;
  status: string;
  sentAt: string | null;
  errorMessage: string | null;
  createdAt: string;
}

// Proxy
export interface ProxyEndpoint {
  id: UUID;
  organizationId: UUID;
  name: string;
  provider: 'openai' | 'anthropic' | 'google_gemini' | 'azure_openai' | 'bedrock' | 'custom';
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

// Component Health
export interface ComponentHealth {
  name: string;
  status: string;
  responseTimeMs: number | null;
  message: string | null;
}

export interface DetailedHealth {
  status: string;
  components: ComponentHealth[];
}

// Billing
export interface BillingStatus {
  planTier: string;
  subscriptionStatus: string | null;
  currentPeriodEnd: string | null;
  monthlyRequestCount: number;
  requestLimit: number | null;
}

export interface CheckoutSessionResponse {
  checkoutUrl: string;
}

export interface CustomerPortalResponse {
  portalUrl: string;
}

// Audit / Compliance
export interface AuditLogEntry {
  id: UUID;
  userId: UUID | null;
  action: string;
  resourceType: string;
  resourceId: UUID | null;
  details: Record<string, unknown>;
  ipAddress: string | null;
  entryHash: string | null;
  createdAt: string;
}

export interface AuditLogFilters {
  action?: string;
  resourceType?: string;
  userId?: string;
  dateFrom?: string;
  dateTo?: string;
  skip?: number;
  limit?: number;
}

export interface ChainVerification {
  valid: boolean;
  checked: number;
  brokenAt: string | null;
}

export interface ComplianceReport {
  id: UUID;
  reportType: string;
  status: string;
  dateFrom: string;
  dateTo: string;
  fileSizeBytes: number | null;
  errorMessage: string | null;
  createdAt: string;
  completedAt: string | null;
}

// Compliance Framework Scoring
export interface RequirementScore {
  name: string;
  violationCount: number;
}

export interface FrameworkScore {
  name: string;
  totalViolations: number;
  requirements: RequirementScore[];
}

export interface ComplianceScores {
  frameworks: FrameworkScore[];
  periodDays: number;
}

// Data Retention
export interface RetentionPolicy {
  id: UUID;
  orgId: UUID;
  proxyRequestsDays: number;
  incidentsDays: number;
  auditLogsDays: number;
  createdAt: string;
  updatedAt: string;
}

export interface RetentionPolicyUpdate {
  proxyRequestsDays?: number;
  incidentsDays?: number;
  auditLogsDays?: number;
}

export interface DataArchive {
  id: UUID;
  orgId: UUID;
  tableName: string;
  startDate: string;
  endDate: string;
  filePath: string;
  rowCount: number;
  fileSizeBytes: number;
  status: string;
  errorMessage: string | null;
  createdAt: string;
}

// Paginated response wrapper
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

// Detection Efficacy
export interface CategoryEfficacy {
  category: string;
  total: number;
  resolved: number;
  dismissed: number;
  open: number;
  falsePositiveRate: number;
  meanTimeToResolveHours: number | null;
}

export interface DailyDetectionCount {
  date: string;
  count: number;
}

export interface DetectionEfficacy {
  categories: CategoryEfficacy[];
  dailyTrend: DailyDetectionCount[];
  overallFalsePositiveRate: number;
  periodDays: number;
}

// Playground
export interface PlaygroundTestRequest {
  request_text: string;
  response_text: string;
  categories: string[];
  model?: string;
}

export interface PlaygroundDetectionHit {
  detected: boolean;
  severity: string;
  category: string;
  action: string;
  title: string;
  description: string;
  details: Record<string, unknown>;
}

export interface PlaygroundTestResponse {
  results: PlaygroundDetectionHit[];
  totalDetections: number;
  categoriesTested: string[];
}

export interface PlaygroundCategories {
  sync: string[];
  async: string[];
}
