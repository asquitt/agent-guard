import { describe, expect, it } from 'vitest';

import { apiUrl, healthUrl, normalizeApiOrigin } from '@/lib/api/url';

describe('API URL contract', () => {
  it('treats the configured value as an origin', () => {
    expect(normalizeApiOrigin('https://deployment.example/')).toBe(
      'https://deployment.example',
    );
  });

  it('normalizes the legacy tracked /api/v1 suffix during migration', () => {
    expect(normalizeApiOrigin('https://deployment.example/api/v1')).toBe(
      'https://deployment.example',
    );
    expect(normalizeApiOrigin('https://deployment.example/api/v1/')).toBe(
      'https://deployment.example',
    );
  });

  it('builds one API prefix and keeps health outside that prefix', () => {
    expect(apiUrl('/incidents/')).toBe('/api/v1/incidents/');
    expect(apiUrl('proxy/v1/chat/completions')).toBe(
      '/api/v1/proxy/v1/chat/completions',
    );
    expect(healthUrl('/detailed')).toBe('/health/detailed');
  });
});
