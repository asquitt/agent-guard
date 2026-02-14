/** Shared UI constants for AgentGuard dashboard. */

/* ── Incident severity ─────────────────────────────────────────── */

export const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
  high: 'bg-orange-500/10 text-orange-400 ring-1 ring-inset ring-orange-500/20',
  medium: 'bg-yellow-500/10 text-yellow-400 ring-1 ring-inset ring-yellow-500/20',
  low: 'bg-green-500/10 text-green-400 ring-1 ring-inset ring-green-500/20',
  info: 'bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20',
};

export const SEVERITY_COLORS_BORDERED: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  low: 'bg-green-500/10 text-green-400 border-green-500/20',
  info: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
};

/* ── Incident status ───────────────────────────────────────────── */

export const STATUS_COLORS: Record<string, string> = {
  open: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
  acknowledged: 'bg-yellow-500/10 text-yellow-400 ring-1 ring-inset ring-yellow-500/20',
  resolved: 'bg-green-500/10 text-green-400 ring-1 ring-inset ring-green-500/20',
  dismissed: 'bg-zinc-500/10 text-zinc-400 ring-1 ring-inset ring-zinc-500/20',
};

/* ── Agent risk tier ───────────────────────────────────────────── */

export const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-500/10 text-green-400',
  medium: 'bg-yellow-500/10 text-yellow-400',
  high: 'bg-orange-500/10 text-orange-400',
  critical: 'bg-red-500/10 text-red-400',
};

/* ── Agent lifecycle status ────────────────────────────────────── */

export const AGENT_STATUS_COLORS: Record<string, string> = {
  draft: 'bg-muted text-muted-foreground',
  testing: 'bg-blue-500/10 text-blue-400',
  production: 'bg-green-500/10 text-green-400',
  deprecated: 'bg-red-500/10 text-red-400',
};

/* ── Detector action modes ─────────────────────────────────────── */

export const MODE_COLORS: Record<string, string> = {
  MONITOR: 'bg-blue-500/10 text-blue-400',
  WARN: 'bg-yellow-500/10 text-yellow-400',
  REDACT: 'bg-orange-500/10 text-orange-400',
  BLOCK: 'bg-red-500/10 text-red-400',
};

/* ── HTTP status code (trace page) ─────────────────────────────── */

export const HTTP_STATUS_COLORS: Record<string, string> = {
  '2': 'text-green-400 bg-green-500/10',
  '4': 'text-yellow-400 bg-yellow-500/10',
  '5': 'text-red-400 bg-red-500/10',
};

/* ── Report / archive row status ───────────────────────────────── */

export const REPORT_STATUS_COLORS: Record<string, string> = {
  completed: 'bg-green-500/10 text-green-400',
  pending: 'bg-yellow-500/10 text-yellow-400',
  generating: 'bg-blue-500/10 text-blue-400',
  failed: 'bg-red-500/10 text-red-400',
};

/* ── Review queue status ───────────────────────────────────────── */

export const REVIEW_STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-500/10 text-yellow-400',
  approved: 'bg-green-500/10 text-green-400',
  rejected: 'bg-red-500/10 text-red-400',
  escalated: 'bg-orange-500/10 text-orange-400',
  expired: 'bg-muted text-muted-foreground',
};

/* ── Compliance verification ───────────────────────────────────── */

export const VERIFICATION_COLORS: Record<string, string> = {
  valid: 'bg-green-500/10 text-green-400',
  invalid: 'bg-red-500/10 text-red-400',
};

/* ── Frameworks badge ──────────────────────────────────────────── */

export const FRAMEWORK_BADGE = 'bg-indigo-500/10 text-indigo-400';

/* ── Chart hex colors (used by Recharts / sparklines) ──────────── */

export const CHART_COLORS = {
  green: '#22c55e',
  red: '#ef4444',
  indigo: '#6366f1',
  amber: '#f59e0b',
  blue: '#3b82f6',
} as const;

/** Map trend direction to a chart color. */
export const TREND_COLORS: Record<string, string> = {
  improving: CHART_COLORS.green,
  degrading: CHART_COLORS.red,
  stable: CHART_COLORS.indigo,
};

/** Series definitions for the analytics chart. */
export const ANALYTICS_SERIES = [
  { key: 'incidents', label: 'Incidents', color: CHART_COLORS.red },
  { key: 'detections', label: 'Detections', color: CHART_COLORS.amber },
  { key: 'errorCount', label: 'Errors', color: CHART_COLORS.indigo },
] as const;

/* ── Category labels ───────────────────────────────────────────── */

export const CATEGORY_LABELS: Record<string, string> = {
  hallucination: 'Hallucination',
  pii_leak: 'PII Leak',
  compliance: 'Compliance',
  cost_anomaly: 'Cost Anomaly',
  loop: 'Loop Detection',
  prompt_injection: 'Prompt Injection',
  prompt_extraction: 'Prompt Extraction',
  toxicity: 'Toxicity',
  tool_call: 'Tool Call',
  mcp_security: 'MCP Security',
  schema_injection: 'Schema Injection',
  sequential_action: 'Sequential Action',
  scope_enforcement: 'Scope Enforcement',
  sycophancy: 'Sycophancy',
  memory_exfiltration: 'Memory Exfiltration',
  confidence_hallucination: 'Confidence Hallucination',
  capability_monitor: 'Capability Monitor',
  instruction_hierarchy: 'Instruction Hierarchy',
  reasoning_trace: 'Reasoning Trace',
  financial_pii: 'Financial PII',
  model_safety_profile: 'Model Safety Profile',
};
