import { describe, expect, it } from 'vitest';
import { ApiError, buildQueryString } from '@/lib/api/client';

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
