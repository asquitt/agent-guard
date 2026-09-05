/**
 * AgentGuard Node.js SDK
 *
 * Source preview client for an explicit AgentGuard deployment.
 */

export { AgentGuardClient } from './client';
export type { AgentGuardClientOptions, IncidentFilters } from './client';

export {
  AgentGuardError,
  AuthenticationError,
  DetectionBlockedError,
  RateLimitError,
  CircuitOpenError,
  ValidationError,
} from './errors';

export type {
  Incident,
  IncidentListResponse,
  ProxyResponse,
  Detector,
} from './types';

export { wrapOpenAI, wrapAnthropic } from './wrap';
export type { WrapOptions } from './wrap';
export { normalizeBaseUrl } from './base-url';

export { AgentGuardCallbackHandler } from './langchain';
export type { AgentGuardCallbackOptions } from './langchain';

export { AgentGuardLangGraphHandler } from './langgraph';
export type { AgentGuardLangGraphOptions } from './langgraph';

export { AgentGuardCrewAIHandler } from './crewai';
export type { AgentGuardCrewAIOptions } from './crewai';
