/**
 * AgentGuard API client for Node.js.
 */

import { raiseForStatus, RateLimitError } from './errors';
import { normalizeBaseUrl } from './base-url';
import type {
  Incident,
  IncidentListResponse,
  ProxyResponse,
} from './types';

export interface AgentGuardClientOptions {
  apiKey: string;
  baseUrl: string;
  /** User access token for access-token-protected management routes. */
  accessToken?: string;
  endpointId?: string;
  timeout?: number;
  maxRetries?: number;
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
  private accessToken: string | undefined;
  private baseUrl: string;
  private endpointId: string | undefined;
  private timeout: number;
  private maxRetries: number;

  constructor(options: AgentGuardClientOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = normalizeBaseUrl(options.baseUrl);
    this.accessToken = options.accessToken;
    this.endpointId = options.endpointId;
    this.timeout = options.timeout ?? 120_000;
    this.maxRetries = options.maxRetries ?? 3;
  }

  private proxyHeaders(): Record<string, string> {
    const h: Record<string, string> = {
      Authorization: `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
    };
    if (this.endpointId) {
      h['X-AgentGuard-Endpoint-Id'] = this.endpointId;
    }
    return h;
  }

  private managementHeaders(): Record<string, string> {
    if (!this.accessToken) {
      throw new TypeError(
        'accessToken is required for AgentGuard management routes',
      );
    }
    return {
      Authorization: `Bearer ${this.accessToken}`,
      'Content-Type': 'application/json',
    };
  }

  private async requestWithRetry(
    url: string,
    init: RequestInit,
  ): Promise<Response> {
    let lastError: Error | undefined;

    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const res = await fetch(url, {
          ...init,
          signal: AbortSignal.timeout(this.timeout),
        });

        if (res.status === 429 && attempt < this.maxRetries - 1) {
          const retryAfter = parseInt(
            res.headers.get('Retry-After') ?? '2',
            10,
          );
          await sleep(Math.min(retryAfter * 1000, 30_000));
          continue;
        }

        if (res.status >= 500 && attempt < this.maxRetries - 1) {
          await sleep(2 ** attempt * 1000);
          continue;
        }

        return res;
      } catch (err) {
        lastError = err as Error;
        if (
          attempt < this.maxRetries - 1 &&
          isTransientError(err)
        ) {
          await sleep(2 ** attempt * 1000);
          continue;
        }
        throw err;
      }
    }

    throw lastError ?? new Error('Unreachable');
  }

  /** Send a request through the AgentGuard proxy. */
  async proxy(
    path: string,
    body: Record<string, unknown>,
  ): Promise<ProxyResponse> {
    const res = await this.requestWithRetry(
      `${this.baseUrl}/api/v1/proxy${path}`,
      { method: 'POST', headers: this.proxyHeaders(), body: JSON.stringify(body) },
    );

    if (!res.ok) {
      raiseForStatus(res.status, await res.text());
    }

    const data = (await res.json()) as Record<string, unknown>;
    return {
      data,
      statusCode: res.status,
      blocked: res.status === 403,
    };
  }

  /** List incidents for the organization. */
  async listIncidents(
    filters: IncidentFilters = {},
  ): Promise<IncidentListResponse> {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) {
      if (v !== undefined) params.set(k, String(v));
    }
    const qs = params.toString() ? `?${params.toString()}` : '';

    const res = await this.requestWithRetry(
      `${this.baseUrl}/api/v1/incidents/${qs}`,
      { headers: this.managementHeaders() },
    );

    if (!res.ok) {
      raiseForStatus(res.status, await res.text());
    }

    return (await res.json()) as IncidentListResponse;
  }

  /** Get a specific incident. */
  async getIncident(incidentId: string): Promise<Incident> {
    const res = await this.requestWithRetry(
      `${this.baseUrl}/api/v1/incidents/${incidentId}`,
      { headers: this.managementHeaders() },
    );

    if (!res.ok) {
      raiseForStatus(res.status, await res.text());
    }

    return (await res.json()) as Incident;
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isTransientError(err: unknown): boolean {
  if (err instanceof TypeError) return true; // fetch network failures
  if (err instanceof RateLimitError) return true;
  const name = (err as { name?: string })?.name;
  return name === 'AbortError' || name === 'TimeoutError';
}
