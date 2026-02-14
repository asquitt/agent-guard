/**
 * AgentGuard SDK error hierarchy.
 */

export class AgentGuardError extends Error {
  readonly statusCode: number | undefined;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'AgentGuardError';
    this.statusCode = statusCode;
  }
}

export class AuthenticationError extends AgentGuardError {
  constructor(message = 'Invalid or expired API key') {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

export class DetectionBlockedError extends AgentGuardError {
  constructor(message = 'Request blocked by detection policy') {
    super(message, 403);
    this.name = 'DetectionBlockedError';
  }
}

export class ValidationError extends AgentGuardError {
  constructor(message = 'Request validation failed') {
    super(message, 422);
    this.name = 'ValidationError';
  }
}

export class RateLimitError extends AgentGuardError {
  readonly retryAfter: number;

  constructor(retryAfter = 2, message = 'Rate limit exceeded') {
    super(message, 429);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class CircuitOpenError extends AgentGuardError {
  constructor(message = 'Circuit breaker open — upstream provider unavailable') {
    super(message, 503);
    this.name = 'CircuitOpenError';
  }
}

/**
 * Throw the appropriate typed error for a non-OK response.
 */
export function raiseForStatus(status: number, body: string): never {
  switch (status) {
    case 401:
      throw new AuthenticationError(body || undefined);
    case 403:
      throw new DetectionBlockedError(body || undefined);
    case 422:
      throw new ValidationError(body || undefined);
    case 429: {
      throw new RateLimitError(undefined, body || undefined);
    }
    case 503:
      throw new CircuitOpenError(body || undefined);
    default:
      throw new AgentGuardError(`HTTP ${status}: ${body}`, status);
  }
}
