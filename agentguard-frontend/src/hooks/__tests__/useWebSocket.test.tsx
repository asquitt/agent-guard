import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockCreateWebSocketTicket = vi.fn();

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));

vi.mock('@/lib/api/websocket', () => ({
  createWebSocketTicket: () => mockCreateWebSocketTicket(),
}));

import { useWebSocket } from '@/hooks/useWebSocket';

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  onopen: (() => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();

  constructor(
    public readonly url: string,
    public readonly protocols?: string | string[],
  ) {
    FakeWebSocket.instances.push(this);
  }
}

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    FakeWebSocket.instances = [];
    localStorage.clear();
    localStorage.setItem('accessToken', 'long-lived-access-jwt');
    mockCreateWebSocketTicket.mockResolvedValue({
      ticket: 'single-use-ticket',
      expiresIn: 30,
    });
    vi.stubGlobal('WebSocket', FakeWebSocket);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('keeps the access JWT out of the WebSocket URL and uses a short-lived protocol ticket', async () => {
    const { unmount } = renderHook(() => useWebSocket());

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const socket = FakeWebSocket.instances[0];

    expect(socket.url).toMatch(/\/ws\/events$/);
    expect(socket.url).not.toContain('?');
    expect(socket.url).not.toContain('long-lived-access-jwt');
    expect(socket.protocols).toEqual([
      'agentguard.v1',
      'agentguard.ticket.single-use-ticket',
    ]);
    expect(JSON.stringify(socket.protocols)).not.toContain('long-lived-access-jwt');

    unmount();
    expect(socket.close).toHaveBeenCalledOnce();
  });

  it.each([
    'wss://archive.example',
    'wss://archive.example/',
    'wss://archive.example/ws',
    'wss://archive.example/ws/events',
  ])('normalizes the configured WebSocket base without duplicating its route: %s', async (configuredUrl) => {
    vi.stubEnv('NEXT_PUBLIC_WS_URL', configuredUrl);

    const { unmount } = renderHook(() => useWebSocket());

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    expect(FakeWebSocket.instances[0].url).toBe('wss://archive.example/ws/events');

    unmount();
  });
});
