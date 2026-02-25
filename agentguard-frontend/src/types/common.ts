/**
 * Common/shared type definitions used across AgentGuard.
 */

// Common types
export type UUID = string;

// Auth
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse {
  access_token: string | null;
  refresh_token: string | null;
  token_type: string;
  mfa_required: boolean;
  mfa_token: string | null;
}

export interface AuthUser {
  id: UUID;
  email: string;
  name: string;
  role: string;
  organizationId: UUID;
  isActive: boolean;
  mfaEnabled: boolean;
  createdAt: string;
}

// MFA
export interface MfaSetupResponse {
  secret: string;
  qr_code: string;
  backup_codes: string[];
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

// Paginated response wrapper
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
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
