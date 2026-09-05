'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { createWebSocketTicket } from '@/lib/api/websocket';
import { ApiError } from '@/lib/api/client';

export interface WebSocketEvent {
  type: 'incident.new' | 'incident.updated' | 'alert.sent' | 'billing.updated' | 'connected';
  data: Record<string, unknown>;
  timestamp?: string;
}

export type WsStatus = 'connecting' | 'connected' | 'disconnected';

/** Derive a path-free WS base URL from env or the current page location. */
function getWsUrl(): string {
  const configuredUrl = process.env.NEXT_PUBLIC_WS_URL?.trim().replace(/\/+$/, '');
  if (configuredUrl) {
    if (configuredUrl.endsWith('/ws/events')) return configuredUrl.slice(0, -'/ws/events'.length);
    if (configuredUrl.endsWith('/ws')) return configuredUrl.slice(0, -'/ws'.length);
    return configuredUrl;
  }
  if (typeof window === 'undefined') return 'ws://localhost:8001';
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}`;
}

const MAX_BACKOFF_MS = 30_000;
const AUTH_CLOSE_CODE = 4001;
const WS_PROTOCOL = 'agentguard.v1';
const WS_TICKET_PROTOCOL_PREFIX = 'agentguard.ticket.';

export function useWebSocket() {
  const { isAuthenticated } = useAuth();
  const [status, setStatus] = useState<WsStatus>('disconnected');
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const connectionGenerationRef = useRef(0);

  const cleanup = useCallback(() => {
    connectionGenerationRef.current += 1;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(async () => {
    if (!mountedRef.current) return;

    cleanup();
    const generation = connectionGenerationRef.current;
    setStatus('connecting');

    let ticket: string;
    try {
      ({ ticket } = await createWebSocketTicket());
    } catch (error) {
      if (!mountedRef.current || generation !== connectionGenerationRef.current) return;
      setStatus('disconnected');

      if (error instanceof ApiError && error.status === 401) return;

      const delay = backoffRef.current;
      backoffRef.current = Math.min(delay * 2, MAX_BACKOFF_MS);
      reconnectTimerRef.current = setTimeout(() => {
        if (mountedRef.current) void connect();
      }, delay);
      return;
    }

    if (!mountedRef.current || generation !== connectionGenerationRef.current) return;

    const ws = new WebSocket(`${getWsUrl()}/ws/events`, [
      WS_PROTOCOL,
      `${WS_TICKET_PROTOCOL_PREFIX}${ticket}`,
    ]);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      backoffRef.current = 1000;
      setStatus('connected');
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const parsed = JSON.parse(event.data) as WebSocketEvent;
        setLastEvent(parsed);
      } catch {
        // Skip malformed messages
      }
    };

    ws.onclose = (event) => {
      if (!mountedRef.current) return;
      setStatus('disconnected');

      // Don't reconnect on auth failures
      if (event.code === AUTH_CLOSE_CODE) return;

      // Exponential backoff reconnect
      const delay = backoffRef.current;
      backoffRef.current = Math.min(delay * 2, MAX_BACKOFF_MS);

      reconnectTimerRef.current = setTimeout(() => {
        if (mountedRef.current) void connect();
      }, delay);
    };

    ws.onerror = () => {
      // onclose will fire after this — reconnect handled there
    };
  }, [cleanup]);

  useEffect(() => {
    mountedRef.current = true;

    if (isAuthenticated) {
      void connect();
    } else {
      cleanup();
      setStatus('disconnected');
    }

    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [isAuthenticated, connect, cleanup]);

  return { status, lastEvent };
}
