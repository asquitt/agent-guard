import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getTrace, listTraces } from '@/lib/api/traces';

describe('trace API paths', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('prefixes the trace collection path exactly once', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await listTraces({ model: 'gpt-4o', limit: 10 });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/traces?model=gpt-4o&limit=10',
      expect.any(Object),
    );
  });

  it('prefixes the trace detail path exactly once', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 'trace-1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await getTrace('trace-1');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/traces/trace-1', expect.any(Object));
  });
});
