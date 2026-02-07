/**
 * Wrap OpenAI and Anthropic clients to route through AgentGuard proxy.
 */

export interface WrapOptions {
  /** AgentGuard API key (ag_live_...) */
  apiKey: string;
  /** Custom AgentGuard proxy URL */
  baseUrl?: string;
  /** Proxy endpoint UUID */
  endpointId?: string;
  /** Custom metadata sent as X-AgentGuard-* headers */
  metadata?: Record<string, string>;
}

/**
 * Wrap an OpenAI client to route all requests through AgentGuard.
 *
 * @example
 * ```ts
 * import OpenAI from 'openai';
 * import { wrapOpenAI } from 'agentguard';
 *
 * const client = new OpenAI({ apiKey: 'sk-...' });
 * const wrapped = wrapOpenAI(client, {
 *   apiKey: 'ag_live_...',
 *   metadata: { userId: 'u_123', agentName: 'support-bot' },
 * });
 * ```
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function wrapOpenAI<T extends Record<string, any>>(
  client: T,
  options: WrapOptions,
): T {
  const base = (options.baseUrl ?? 'https://api.agentguard.app').replace(
    /\/$/,
    '',
  );
  const proxyUrl = `${base}/api/v1/proxy/openai/v1`;

  // OpenAI SDK stores base URL
  (client as Record<string, unknown>).baseURL = proxyUrl;

  const headers = buildHeaders(options);
  applyHeaders(client, headers);
  return client;
}

/**
 * Wrap an Anthropic client to route all requests through AgentGuard.
 *
 * @example
 * ```ts
 * import Anthropic from '@anthropic-ai/sdk';
 * import { wrapAnthropic } from 'agentguard';
 *
 * const client = new Anthropic({ apiKey: 'sk-ant-...' });
 * const wrapped = wrapAnthropic(client, {
 *   apiKey: 'ag_live_...',
 *   metadata: { sessionId: 'sess_456' },
 * });
 * ```
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function wrapAnthropic<T extends Record<string, any>>(
  client: T,
  options: WrapOptions,
): T {
  const base = (options.baseUrl ?? 'https://api.agentguard.app').replace(
    /\/$/,
    '',
  );
  const proxyUrl = `${base}/api/v1/proxy/anthropic/v1`;

  // Anthropic SDK stores base URL differently
  (client as Record<string, unknown>)._baseURL = proxyUrl;

  const headers = buildHeaders(options);
  applyHeaders(client, headers);
  return client;
}

function buildHeaders(options: WrapOptions): Record<string, string> {
  const h: Record<string, string> = {
    Authorization: `Bearer ${options.apiKey}`,
  };
  if (options.endpointId) {
    h['X-AgentGuard-Endpoint-Id'] = options.endpointId;
  }
  if (options.metadata) {
    for (const [key, value] of Object.entries(options.metadata)) {
      h[`X-AgentGuard-${key}`] = value;
    }
  }
  return h;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function applyHeaders(client: Record<string, any>, headers: Record<string, string>): void {
  if (!client._customHeaders || typeof client._customHeaders !== 'object') {
    client._customHeaders = {};
  }
  Object.assign(client._customHeaders as Record<string, string>, headers);
}
