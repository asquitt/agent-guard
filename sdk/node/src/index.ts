/**
 * AgentGuard Node.js SDK
 *
 * AI agent security monitoring for financial services.
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
