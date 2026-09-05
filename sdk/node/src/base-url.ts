/** Validate and normalize an explicit AgentGuard deployment origin. */
export function normalizeBaseUrl(baseUrl: string): string {
  let parsed: URL;
  try {
    parsed = new URL(baseUrl.trim().replace(/\/+$/, ''));
  } catch {
    throw new TypeError(
      'baseUrl must be an absolute HTTP(S) AgentGuard deployment origin',
    );
  }

  if (
    !['http:', 'https:'].includes(parsed.protocol) ||
    parsed.username ||
    parsed.password ||
    (parsed.pathname !== '/' && parsed.pathname !== '') ||
    parsed.search ||
    parsed.hash
  ) {
    throw new TypeError(
      'baseUrl must be an absolute HTTP(S) AgentGuard deployment origin',
    );
  }

  const loopbackHosts = new Set(['localhost', '127.0.0.1', '[::1]']);
  if (parsed.protocol === 'http:' && !loopbackHosts.has(parsed.hostname)) {
    throw new TypeError(
      'baseUrl must use HTTPS unless the AgentGuard deployment is on loopback',
    );
  }

  return parsed.origin;
}
