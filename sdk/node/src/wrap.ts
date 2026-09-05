/**
 * Wrap OpenAI and Anthropic clients to route through AgentGuard proxy.
 */

import { normalizeBaseUrl } from './base-url';

export interface WrapOptions {
  /** AgentGuard API key (ag_live_...) */
  apiKey: string;
  /** Base URL of the AgentGuard deployment (for example, http://localhost:8001) */
  baseUrl: string;
  /** Proxy endpoint UUID */
  endpointId?: string;
  /** Custom metadata sent as X-AgentGuard-* headers */
  metadata?: Record<string, string>;
}

/**
 * Configure an OpenAI client clone for AgentGuard's tracked OpenAI routes.
 *
 * @example
 * ```ts
 * import OpenAI from 'openai';
 * import { wrapOpenAI } from 'agentguard';
 *
 * const agentguardKey = 'ag_live_...';
 * const client = new OpenAI({ apiKey: agentguardKey });
 * const wrapped = wrapOpenAI(client, {
 *   apiKey: agentguardKey,
 *   baseUrl: 'http://localhost:8001',
 *   metadata: { userId: 'u_123', agentName: 'support-bot' },
 * });
 * ```
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function wrapOpenAI<T extends Record<string, any>>(
  client: T,
  options: WrapOptions,
): T {
  const base = normalizeBaseUrl(options.baseUrl);
  const proxyUrl = `${base}/api/v1/proxy/v1`;
  return configureClient(client, options, proxyUrl);
}

/**
 * Configure an Anthropic client clone for AgentGuard's tracked messages route.
 *
 * @example
 * ```ts
 * import Anthropic from '@anthropic-ai/sdk';
 * import { wrapAnthropic } from 'agentguard';
 *
 * const agentguardKey = 'ag_live_...';
 * const client = new Anthropic({ apiKey: agentguardKey });
 * const wrapped = wrapAnthropic(client, {
 *   apiKey: agentguardKey,
 *   baseUrl: 'http://localhost:8001',
 *   metadata: { sessionId: 'sess_456' },
 * });
 * ```
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function wrapAnthropic<T extends Record<string, any>>(
  client: T,
  options: WrapOptions,
): T {
  const base = normalizeBaseUrl(options.baseUrl);
  const proxyUrl = `${base}/api/v1/proxy`;
  return configureClient(client, options, proxyUrl);
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

interface ProviderCloneOptions {
  apiKey: string;
  baseURL: string;
  defaultHeaders: Record<string, string>;
}

function configureClient<T>(
  client: T,
  options: WrapOptions,
  proxyUrl: string,
): T {
  const configurable = client as {
    withOptions?: (options: ProviderCloneOptions) => T;
  };
  if (typeof configurable.withOptions !== 'function') {
    throw new TypeError(
      'AgentGuard wrappers require an official OpenAI or Anthropic client with withOptions()',
    );
  }

  return configurable.withOptions({
    apiKey: options.apiKey,
    baseURL: proxyUrl,
    defaultHeaders: buildHeaders(options),
  });
}
