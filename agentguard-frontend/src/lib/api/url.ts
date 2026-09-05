export const API_PREFIX = '/api/v1';

/**
 * NEXT_PUBLIC_API_URL is an origin, not an API-prefix URL.
 * Strip the legacy tracked `/api/v1` suffix so existing deployments do not
 * produce `/api/v1/api/v1/...` while they migrate to the canonical contract.
 */
export function normalizeApiOrigin(configuredUrl: string | undefined): string {
  const trimmed = configuredUrl?.trim().replace(/\/+$/, '') ?? '';
  if (trimmed.endsWith(API_PREFIX)) {
    return trimmed.slice(0, -API_PREFIX.length);
  }
  return trimmed;
}

export const API_ORIGIN = normalizeApiOrigin(process.env.NEXT_PUBLIC_API_URL);

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_ORIGIN}${API_PREFIX}${normalizedPath}`;
}

export function healthUrl(path = ''): string {
  const normalizedPath = path && !path.startsWith('/') ? `/${path}` : path;
  return `${API_ORIGIN}/health${normalizedPath}`;
}

export function browserApiOrigin(): string {
  if (API_ORIGIN) return API_ORIGIN;
  return typeof window === 'undefined' ? '' : window.location.origin;
}
