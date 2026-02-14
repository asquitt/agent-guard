/**
 * API client with authentication handling and automatic token refresh.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';
const API_PREFIX = '/api/v1';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('accessToken');
}

function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('refreshToken');
}

function storeTokens(access: string, refresh: string) {
  localStorage.setItem('accessToken', access);
  localStorage.setItem('refreshToken', refresh);
}

function clearTokens() {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
}

// Prevent concurrent refresh attempts
let refreshPromise: Promise<boolean> | null = null;

export { clearTokens };

export async function tryRefreshToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) return false;

    try {
      const res = await fetch(`${API_BASE_URL}${API_PREFIX}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return false;

      const tokens = await res.json();
      storeTokens(tokens.access_token, tokens.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${API_PREFIX}${endpoint}`, {
    ...options,
    headers,
  });

  // On 401, attempt token refresh and retry once
  if (response.status === 401 && token) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      const newToken = getAccessToken();
      const { Authorization: _, ...callerHeaders } = (options.headers || {}) as Record<string, string>;
      const retryHeaders: HeadersInit = {
        'Content-Type': 'application/json',
        ...callerHeaders,
        ...(newToken && { Authorization: `Bearer ${newToken}` }),
      };
      const retryResponse = await fetch(`${API_BASE_URL}${API_PREFIX}${endpoint}`, {
        ...options,
        headers: retryHeaders,
      });
      if (retryResponse.ok) return retryResponse.json();
      // Retry also failed — clear tokens and redirect to login
      clearTokens();
      if (typeof window !== 'undefined') window.location.href = '/login';
      throw new ApiError(401, 'Session expired');
    }
    // Refresh failed — clear tokens and redirect
    clearTokens();
    if (typeof window !== 'undefined') window.location.href = '/login';
    throw new ApiError(401, 'Session expired');
  }

  // On 429, notify user and retry once after the Retry-After delay (max 10s)
  if (response.status === 429) {
    const retryAfter = Math.min(
      parseInt(response.headers.get('Retry-After') ?? '2', 10) * 1000,
      10000,
    );
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('api:rate-limited', { detail: { retryAfter } }));
    }
    await new Promise((r) => setTimeout(r, retryAfter));
    const retryResponse = await fetch(`${API_BASE_URL}${API_PREFIX}${endpoint}`, {
      ...options,
      headers,
    });
    if (retryResponse.ok) return retryResponse.json();
    const retryError = await retryResponse.json().catch(() => ({ detail: 'Rate limited' }));
    throw new ApiError(retryResponse.status, retryError.detail || 'Rate limited');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }

  return response.json();
}

export function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}
