import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import StatusPage from '@/app/status/page';

describe('deployment health status', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('renders only returned component checks and hides backend exception details', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 'unhealthy',
          components: [
            {
              name: 'database',
              status: 'error',
              response_time_ms: 12,
              message: 'postgresql://admin:secret@private-db.example/internal',
            },
          ],
        }),
        { status: 503, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    const { container } = render(<StatusPage />);

    expect(screen.getByText(/mothballed as a standalone product/i)).toBeInTheDocument();
    expect(await screen.findByText('A configured check reported an error')).toBeInTheDocument();
    expect(screen.getByText('Database connectivity')).toBeInTheDocument();
    expect(screen.queryByText('API Server')).not.toBeInTheDocument();
    expect(screen.queryByText('LLM Proxy Gateway')).not.toBeInTheDocument();
    expect(container.textContent).not.toContain('secret');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/health/detailed',
      { cache: 'no-store' },
    );
  });

  it('reports unknown rather than an outage when the health endpoint cannot be read', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(
      new Error('connect ECONNREFUSED private-api.internal:8000'),
    );

    const { container } = render(<StatusPage />);

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Health state unknown'));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'The configured health endpoint could not be reached or returned an unreadable response.',
    );
    expect(container.textContent).not.toContain('private-api.internal');
    expect(container.textContent).not.toContain('ECONNREFUSED');
    expect(screen.queryByText(/outage/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/operational/i)).not.toBeInTheDocument();
  });

  it('does not expose a JSON parser error when a frontend route answers the health request', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('<!DOCTYPE html><title>Not Found</title>', {
        status: 404,
        headers: { 'Content-Type': 'text/html' },
      }),
    );

    const { container } = render(<StatusPage />);

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Health state unknown'));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'The configured health endpoint could not be reached or returned an unreadable response.',
    );
    expect(container.textContent).not.toContain('Unexpected token');
    expect(container.textContent).not.toContain('DOCTYPE');
  });
});
