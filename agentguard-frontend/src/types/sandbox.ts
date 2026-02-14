export interface SandboxCapability {
  type: string;
  target: string;
  expires_at?: string | null;
}

export interface ResourceLimits {
  cpu_shares: number;
  memory_mb: number;
  max_tokens: number;
  timeout_seconds: number;
}

export interface NetworkPolicy {
  allowed_hosts: string[];
  allowed_ports: number[];
  deny_all_egress: boolean;
}

export interface SandboxData {
  id: string;
  name: string;
  description: string | null;
  status: string;
  agentId: string | null;
  image: string;
  isActive: boolean;
  capabilities: SandboxCapability[];
  resourceLimits: ResourceLimits;
  networkPolicy: NetworkPolicy;
  environment: Record<string, string>;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface SandboxExecutionData {
  id: string;
  sandboxId: string;
  status: string;
  containerId: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  exitCode: number | null;
  trigger: string;
  errorMessage: string | null;
  resourceUsage: {
    cpu_seconds: number;
    memory_peak_mb: number;
    tokens_used: number;
    network_bytes: number;
  };
  createdAt: string;
  updatedAt: string;
}

export interface SandboxAuditLogEntry {
  id: string;
  executionId: string;
  actionType: string;
  actionDetail: Record<string, unknown>;
  allowed: boolean;
  capabilityMatched: string | null;
  entryHash: string | null;
  timestamp: string;
}

export interface SandboxStats {
  totalSandboxes: number;
  activeSandboxes: number;
  totalExecutions: number;
  runningExecutions: number;
  deniedActions: number;
  totalTokensUsed: number;
}

export interface SandboxFilters {
  status?: string;
  agentId?: string;
  skip?: number;
  limit?: number;
}

export type SandboxStatus = 'pending' | 'provisioning' | 'running' | 'paused' | 'terminated' | 'failed';
