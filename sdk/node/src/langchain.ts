/**
 * LangChain.js callback handler for AgentGuard.
 *
 * Buffers selected LangChain callback events and attempts best-effort delivery
 * to the AgentGuard ingest API.
 *
 * @example
 * ```ts
 * import { ChatOpenAI } from '@langchain/openai';
 * import { AgentGuardCallbackHandler } from 'agentguard';
 *
 * const handler = new AgentGuardCallbackHandler({
 *   apiKey: 'ag_live_...',
 *   baseUrl: 'http://localhost:8001',
 * });
 * const llm = new ChatOpenAI({ callbacks: [handler] });
 * await llm.invoke('Summarize Q4 financials');
 * ```
 */

import { randomUUID } from 'node:crypto';

import { normalizeBaseUrl } from './base-url';

interface SDKEvent {
  type: string;
  run_id: string;
  session_id: string;
  timestamp: number;
  metadata: Record<string, string>;
  [key: string]: unknown;
}

export interface AgentGuardCallbackOptions {
  apiKey: string;
  baseUrl: string;
  endpointId?: string;
  metadata?: Record<string, string>;
  flushOnChainEnd?: boolean;
}

export class AgentGuardCallbackHandler {
  private apiKey: string;
  private baseUrl: string;
  private endpointId: string | undefined;
  private metadata: Record<string, string>;
  private flushOnChainEnd: boolean;

  private sessionId: string;
  private events: SDKEvent[] = [];
  private runStarts: Map<string, number> = new Map();
  private chainDepth = 0;

  name = 'AgentGuardCallbackHandler';

  constructor(options: AgentGuardCallbackOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = normalizeBaseUrl(options.baseUrl);
    this.endpointId = options.endpointId;
    this.metadata = options.metadata ?? {};
    this.flushOnChainEnd = options.flushOnChainEnd ?? true;
    this.sessionId = randomUUID();
  }

  private emit(partial: Record<string, unknown> & { type: string; run_id: string }): void {
    const event: SDKEvent = {
      ...partial,
      type: partial.type,
      run_id: partial.run_id,
      session_id: this.sessionId,
      timestamp: Date.now() / 1000,
      metadata: this.metadata,
    };
    this.events.push(event);
  }

  private async flush(raiseOnError = false): Promise<boolean> {
    if (this.events.length === 0) return true;
    const batch = [...this.events];
    this.events = [];
    try {
      const headers: Record<string, string> = {
        Authorization: `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      };
      if (this.endpointId) {
        headers['X-AgentGuard-Endpoint-Id'] = this.endpointId;
      }
      const response = await fetch(`${this.baseUrl}/api/v1/ingest/events`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ events: batch }),
        signal: AbortSignal.timeout(10_000),
      });
      if (!response.ok) {
        throw new Error(`AgentGuard ingest failed with HTTP ${response.status}`);
      }
      return true;
    } catch (error) {
      this.events = [...batch, ...this.events];
      if (raiseOnError) throw error;
      return false;
    }
  }

  // ── LLM Events ──────────────────────────────────────────────

  handleLLMStart(
    _llm: Record<string, unknown>,
    prompts: string[],
    runId: string,
  ): void {
    this.runStarts.set(runId, Date.now());
    this.emit({
      type: 'llm_start',
      run_id: runId,
      model: String((_llm?.kwargs as Record<string, unknown>)?.model_name ?? ''),
      prompt_count: prompts.length,
      prompts: prompts.map((p) => p.slice(0, 500)),
    });
  }

  handleLLMEnd(output: Record<string, unknown>, runId: string): void {
    const start = this.runStarts.get(runId) ?? Date.now();
    this.runStarts.delete(runId);
    this.emit({
      type: 'llm_end',
      run_id: runId,
      duration_ms: Date.now() - start,
      token_usage: (output?.llmOutput as Record<string, unknown>)?.tokenUsage ?? {},
    });
  }

  handleLLMError(error: Error, runId: string): void {
    this.runStarts.delete(runId);
    this.emit({
      type: 'llm_error',
      run_id: runId,
      error: error.message.slice(0, 500),
      error_type: error.name,
    });
  }

  // ── Chat Model Events ───────────────────────────────────────

  handleChatModelStart(
    _llm: Record<string, unknown>,
    messages: unknown[][],
    runId: string,
  ): void {
    this.runStarts.set(runId, Date.now());
    const flat = messages.flat().map((m) => {
      const msg = m as Record<string, unknown>;
      return {
        role: String(msg.type ?? 'unknown'),
        content: String(msg.content ?? '').slice(0, 500),
      };
    });
    this.emit({
      type: 'chat_model_start',
      run_id: runId,
      model: String((_llm?.kwargs as Record<string, unknown>)?.model_name ?? ''),
      message_count: flat.length,
      messages: flat.slice(0, 20),
    });
  }

  // ── Chain Events ────────────────────────────────────────────

  handleChainStart(chain: Record<string, unknown>, _inputs: unknown, runId: string): void {
    this.chainDepth++;
    this.runStarts.set(runId, Date.now());
    this.emit({
      type: 'chain_start',
      run_id: runId,
      chain_type: String(chain?.name ?? (Array.isArray(chain?.id) ? chain.id[chain.id.length - 1] : 'unknown')),
      depth: this.chainDepth,
    });
  }

  async handleChainEnd(_outputs: unknown, runId: string): Promise<void> {
    const start = this.runStarts.get(runId) ?? Date.now();
    this.runStarts.delete(runId);
    this.emit({
      type: 'chain_end',
      run_id: runId,
      duration_ms: Date.now() - start,
      depth: this.chainDepth,
    });
    this.chainDepth = Math.max(0, this.chainDepth - 1);
    if (this.chainDepth === 0 && this.flushOnChainEnd) {
      await this.flush();
    }
  }

  async handleChainError(error: Error, runId: string): Promise<void> {
    this.runStarts.delete(runId);
    this.chainDepth = Math.max(0, this.chainDepth - 1);
    this.emit({
      type: 'chain_error',
      run_id: runId,
      error: error.message.slice(0, 500),
      error_type: error.name,
    });
    await this.flush();
  }

  // ── Tool Events ─────────────────────────────────────────────

  handleToolStart(tool: Record<string, unknown>, input: string, runId: string): void {
    this.runStarts.set(runId, Date.now());
    this.emit({
      type: 'tool_start',
      run_id: runId,
      tool_name: String(tool?.name ?? 'unknown'),
      input: input.slice(0, 500),
    });
  }

  handleToolEnd(output: string, runId: string): void {
    const start = this.runStarts.get(runId) ?? Date.now();
    this.runStarts.delete(runId);
    this.emit({
      type: 'tool_end',
      run_id: runId,
      duration_ms: Date.now() - start,
      output: output.slice(0, 500),
    });
  }

  handleToolError(error: Error, runId: string): void {
    this.runStarts.delete(runId);
    this.emit({
      type: 'tool_error',
      run_id: runId,
      error: error.message.slice(0, 500),
      error_type: error.name,
    });
  }

  // ── Agent Events ────────────────────────────────────────────

  handleAgentAction(action: Record<string, unknown>, runId: string): void {
    this.emit({
      type: 'agent_action',
      run_id: runId,
      tool: String(action?.tool ?? ''),
      tool_input: String(action?.toolInput ?? '').slice(0, 500),
      log: String(action?.log ?? '').slice(0, 500),
    });
  }

  async handleAgentEnd(output: Record<string, unknown>, runId: string): Promise<void> {
    this.emit({
      type: 'agent_finish',
      run_id: runId,
      output: String(output?.returnValues ?? output).slice(0, 500),
    });
    await this.flush();
  }

  // ── Lifecycle ───────────────────────────────────────────────

  /** Manually flush any buffered events. */
  async manualFlush(): Promise<void> {
    await this.flush(true);
  }
}
