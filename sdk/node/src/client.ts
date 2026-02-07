/**
 * AgentGuard API client for Node.js.
 */

export interface AgentGuardClientOptions {
  apiKey: string;
  baseUrl?: string;
  endpointId?: string;
  timeout?: number;
}

export interface IncidentFilters {
  severity?: string;
  status?: string;
  category?: string;
  skip?: number;
  limit?: number;
}

export class AgentGuardClient {
  private apiKey: string;
  private baseUrl: string;
  private endpointId: string | undefined;
  private timeout: number;

  constructor(options: AgentGuardClientOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl ?? 'https://api.agentguard.app').replace(
      /\/$/,
      '',
    );
    this.endpointId = options.endpointId;
    this.timeout = options.timeout ?? 120_000;
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = {
      Authorization: `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
    };
    if (this.endpointId) {
      h['X-AgentGuard-Endpoint-Id'] = this.endpointId;
    }
    return h;
  }

  /** Send a request through the AgentGuard proxy. */
  async proxy(path: string, body: Record<string, unknown>): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/api/v1/proxy${path}`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!res.ok) {
      throw new Error(`AgentGuard proxy error: ${res.status} ${res.statusText}`);
    }
    return res.json();
  }

  /** List incidents for the organization. */
  async listIncidents(filters: IncidentFilters = {}): Promise<unknown> {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) {
      if (v !== undefined) params.set(k, String(v));
    }
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${this.baseUrl}/api/v1/incidents/${qs}`, {
      headers: this.headers(),
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!res.ok) {
      throw new Error(`AgentGuard API error: ${res.status} ${res.statusText}`);
    }
    return res.json();
  }

  /** Get a specific incident. */
  async getIncident(incidentId: string): Promise<unknown> {
    const res = await fetch(
      `${this.baseUrl}/api/v1/incidents/${incidentId}`,
      {
        headers: this.headers(),
        signal: AbortSignal.timeout(this.timeout),
      },
    );
    if (!res.ok) {
      throw new Error(`AgentGuard API error: ${res.status} ${res.statusText}`);
    }
    return res.json();
  }
}
