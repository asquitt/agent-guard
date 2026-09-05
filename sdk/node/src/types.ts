/**
 * AgentGuard SDK response types.
 */

export interface Incident {
  id: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  category: string;
  title: string;
  status: 'open' | 'acknowledged' | 'resolved' | 'dismissed';
  description: string | null;
  actionTaken: string | null;
  createdAt: string;
  updatedAt: string;
  proxyRequestId: string | null;
  detectorId: string | null;
  sandboxExecutionId: string | null;
  resolvedAt: string | null;
}

export interface IncidentListResponse {
  items: Incident[];
  total: number;
}

export interface ProxyResponse {
  data: Record<string, unknown>;
  statusCode: number;
  blocked: boolean;
}

export interface Detector {
  id: string;
  name: string;
  category: string;
  isActive: boolean;
  actionMode: string;
  config: Record<string, unknown>;
}
