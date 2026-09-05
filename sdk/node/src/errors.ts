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
  const { message, type } = parseErrorBody(body);
  switch (status) {
    case 401:
      throw new AuthenticationError(message || undefined);
    case 403:
      if (type.includes('detection')) {
        throw new DetectionBlockedError(message || undefined);
      }
      throw new AgentGuardError(message || 'Forbidden', 403);
    case 422:
      throw new ValidationError(message || undefined);
    case 429: {
      throw new RateLimitError(undefined, message || undefined);
    }
    case 503:
      if (type.includes('circuit')) {
        throw new CircuitOpenError(message || undefined);
      }
      throw new AgentGuardError(message || 'Service unavailable', 503);
    default:
      throw new AgentGuardError(`HTTP ${status}: ${message || body}`, status);
  }
}

function parseErrorBody(body: string): { message: string; type: string } {
  try {
    const parsed = JSON.parse(body) as {
      detail?: string | { error?: string; message?: string; type?: string };
      error?: string | { error?: string; message?: string; type?: string };
    };
    const candidate = parsed.error ?? parsed.detail;
    if (typeof candidate === 'string') {
      return { message: candidate, type: '' };
    }
    if (candidate && typeof candidate === 'object') {
      return {
        message: candidate.message ?? candidate.error ?? body,
        type: candidate.type ?? '',
      };
    }
  } catch {
    // Non-JSON provider or proxy error body.
  }
  return { message: body, type: '' };
}
