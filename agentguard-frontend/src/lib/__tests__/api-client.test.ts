import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch, buildQueryString } from '@/lib/api/client';

describe('apiFetch', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('returns undefined for a successful response with no content', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    await expect(apiFetch<void>('/auth/logout', { method: 'POST' })).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/logout',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('parses a JSON success response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(apiFetch<{ ok: boolean }>('/health')).resolves.toEqual({ ok: true });
  });

  it('handles no-content after refreshing an expired access token', async () => {
    localStorage.setItem('accessToken', 'expired');
    localStorage.setItem('refreshToken', 'refresh');
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Unauthorized' }), { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: 'fresh', refresh_token: 'fresh-refresh' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(apiFetch<void>('/auth/logout', { method: 'POST' })).resolves.toBeUndefined();
    expect(localStorage.getItem('accessToken')).toBe('fresh');
  });

  it('handles no-content after a rate-limit retry', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(null, { status: 429, headers: { 'Retry-After': '0' } }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(apiFetch<void>('/detectors/id', { method: 'DELETE' })).resolves.toBeUndefined();
  });
});

describe('buildQueryString', () => {
  it('builds query string from params', () => {
    const result = buildQueryString({ page: 1, status: 'active' });
    expect(result).toBe('?page=1&status=active');
  });

  it('skips null and undefined values', () => {
    const result = buildQueryString({ page: 1, status: null, sort: undefined });
    expect(result).toBe('?page=1');
  });

  it('returns empty string when all values are null/undefined', () => {
    const result = buildQueryString({ a: null, b: undefined });
    expect(result).toBe('');
  });

  it('returns empty string for empty params', () => {
    const result = buildQueryString({});
    expect(result).toBe('');
  });

  it('converts non-string values to strings', () => {
    const result = buildQueryString({ count: 42, enabled: true });
    expect(result).toBe('?count=42&enabled=true');
  });
});

describe('ApiError', () => {
  it('has status and message properties', () => {
    const error = new ApiError(404, 'Not found');

    expect(error.status).toBe(404);
    expect(error.message).toBe('Not found');
    expect(error.name).toBe('ApiError');
  });

  it('is an instance of Error', () => {
    const error = new ApiError(500, 'Server error');

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiError);
  });
});
