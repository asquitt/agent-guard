/**
 * Detector-related type definitions.
 */

import type { UUID } from './common';

export type DetectorCategory = 'hallucination' | 'pii_leak' | 'compliance' | 'cost_anomaly' | 'loop' | 'prompt_injection' | 'prompt_extraction' | 'toxicity' | 'tool_call' | 'mcp_security' | 'schema_injection' | 'sequential_action' | 'scope_enforcement' | 'sycophancy' | 'memory_exfiltration' | 'confidence_hallucination' | 'capability_monitor' | 'instruction_hierarchy' | 'reasoning_trace' | 'financial_pii' | 'model_safety_profile';

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
