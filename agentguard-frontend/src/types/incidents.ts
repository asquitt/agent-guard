/**
 * Incident-related type definitions.
 */

import type { UUID } from './common';

// Incidents
export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type IncidentStatus = 'open' | 'acknowledged' | 'resolved' | 'dismissed';
export type IncidentCategory = 'hallucination' | 'pii_leak' | 'compliance' | 'cost_anomaly' | 'loop' | 'prompt_injection' | 'prompt_extraction' | 'toxicity' | 'tool_call' | 'mcp_security' | 'schema_injection' | 'sequential_action' | 'scope_enforcement' | 'sycophancy' | 'memory_exfiltration' | 'confidence_hallucination' | 'capability_monitor' | 'instruction_hierarchy' | 'reasoning_trace' | 'financial_pii' | 'model_safety_profile';

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
  sort?: string;
  dir?: string;
  skip?: number;
  limit?: number;
}
