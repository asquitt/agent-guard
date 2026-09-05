/**
 * CrewAI-style multi-agent handler for AgentGuard (Node.js).
 *
 * Buffers selected workflow events and attempts best-effort delivery to the
 * AgentGuard ingest API.
 *
 * @example
 * ```ts
 * import { AgentGuardCrewAIHandler } from 'agentguard';
 *
 * const handler = new AgentGuardCrewAIHandler({
 *   apiKey: 'ag_live_...',
 *   baseUrl: 'http://localhost:8001',
 * });
 * const result = await handler.run(crew);
 * ```
 */

import { randomUUID } from 'node:crypto';

import { normalizeBaseUrl } from './base-url';

interface SDKEvent {
  type: string;
  session_id: string;
  timestamp: number;
  metadata: Record<string, string>;
  [key: string]: unknown;
}

export interface AgentGuardCrewAIOptions {
  apiKey: string;
  baseUrl: string;
  endpointId?: string;
  metadata?: Record<string, string>;
}

export class AgentGuardCrewAIHandler {
  private apiKey: string;
  private baseUrl: string;
  private endpointId: string | undefined;
  private metadata: Record<string, string>;

  private sessionId: string;
  private events: SDKEvent[] = [];

  constructor(options: AgentGuardCrewAIOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = normalizeBaseUrl(options.baseUrl);
    this.endpointId = options.endpointId;
    this.metadata = options.metadata ?? {};
    this.sessionId = randomUUID();
  }

  private emit(event_type: string, extra: Record<string, unknown> = {}): void {
    this.events.push({
      type: event_type,
      session_id: this.sessionId,
      timestamp: Date.now() / 1000,
      metadata: this.metadata,
      ...extra,
    });
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

  /** Track a task starting execution. */
  onTaskStart(taskDescription: string, agentRole: string, agentGoal?: string): void {
    this.emit('crewai_task_start', {
      task_description: taskDescription.slice(0, 500),
      agent_role: agentRole.slice(0, 500),
      agent_goal: (agentGoal ?? '').slice(0, 500),
    });
  }

  /** Track a task completing. */
  onTaskEnd(taskDescription: string, output: string, durationMs: number): void {
    this.emit('crewai_task_end', {
      task_description: taskDescription.slice(0, 500),
      output: output.slice(0, 500),
      duration_ms: durationMs,
    });
  }

  /** Track a tool being used by an agent. */
  onToolUse(toolName: string, toolInput: string, toolOutput: string): void {
    this.emit('crewai_tool_use', {
      tool_name: toolName.slice(0, 500),
      tool_input: toolInput.slice(0, 500),
      tool_output: toolOutput.slice(0, 500),
    });
  }

  /**
   * Run a multi-agent crew and capture events.
   *
   * Expects an object with a `kickoff()` method (CrewAI Crew interface).
   */
  async run<T>(crew: { kickoff: (...args: unknown[]) => Promise<T> | T }, ...args: unknown[]): Promise<T> {
    const agents = (crew as Record<string, unknown>).agents as unknown[] | undefined;
    const tasks = (crew as Record<string, unknown>).tasks as unknown[] | undefined;

    this.emit('crewai_crew_start', {
      agent_count: agents?.length ?? 0,
      task_count: tasks?.length ?? 0,
    });

    const start = Date.now();
    try {
      const result = await crew.kickoff(...args);
      this.emit('crewai_crew_end', {
        duration_ms: Date.now() - start,
        output: String(result).slice(0, 500),
      });
      await this.flush();
      return result;
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      this.emit('crewai_crew_error', {
        error: err.message.slice(0, 500),
        error_type: err.name,
        duration_ms: Date.now() - start,
      });
      await this.flush();
      throw error;
    }
  }

  /** Manually flush any buffered events. */
  async manualFlush(): Promise<void> {
    await this.flush(true);
  }
}
