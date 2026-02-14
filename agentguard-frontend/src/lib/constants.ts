/** Shared UI constants for AgentGuard dashboard. */

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

export const STATUS_COLORS: Record<string, string> = {
  open: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
  acknowledged: 'bg-yellow-500/10 text-yellow-400 ring-1 ring-inset ring-yellow-500/20',
  resolved: 'bg-green-500/10 text-green-400 ring-1 ring-inset ring-green-500/20',
  dismissed: 'bg-zinc-500/10 text-zinc-400 ring-1 ring-inset ring-zinc-500/20',
};

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
