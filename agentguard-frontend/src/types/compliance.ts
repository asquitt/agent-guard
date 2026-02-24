/**
 * Compliance, audit, and governance type definitions.
 */

import type { UUID } from './common';

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

// Governance - OWASP
export interface OWASPRisk {
  id: string;
  name: string;
  description: string;
  coverage: 'full' | 'partial' | 'none';
  mappedCategories: string[];
  incidentsDetected: number;
  incidentsResolved: number;
  activeIncidents: number;
}

export interface OWASPCompliance {
  risks: OWASPRisk[];
  coveragePercentage: number;
  coveredRisks: number;
  totalRisks: number;
  periodDays: number;
}

// Governance - MITRE ATLAS
export interface ATLASTechnique {
  id: string;
  name: string;
  tactic: string;
  description: string;
  coverage: 'full' | 'partial' | 'none';
  mappedCategories: string[];
  incidentsDetected: number;
  severityBreakdown: Record<string, number>;
}

export interface ThreatMapping {
  techniques: ATLASTechnique[];
  coveragePercentage: number;
  totalTechniques: number;
  coveredTechniques: number;
  periodDays: number;
}

// Governance - Cross-Framework Compliance
export interface FrameworkRequirement {
  framework: string;
  requirementId: string;
  requirementName: string;
  status: 'compliant' | 'partial' | 'non_compliant';
  mappedCategories: string[];
  violations: number;
  lastViolation: string | null;
}

export interface ComplianceMatrix {
  requirements: FrameworkRequirement[];
  overallCompliance: number;
  frameworksAssessed: number;
  periodDays: number;
}

export interface FrameworkSummaryItem {
  framework: string;
  displayName: string;
  totalRequirements: number;
  compliant: number;
  partial: number;
  nonCompliant: number;
  compliancePercentage: number;
  totalViolations: number;
}

export interface FrameworkSummaryResponse {
  frameworks: FrameworkSummaryItem[];
  overallCompliance: number;
  periodDays: number;
}

export interface EnforcementDeadline {
  framework: string;
  milestone: string;
  date: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  status: 'upcoming' | 'active' | 'passed';
}
