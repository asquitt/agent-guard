'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';

export interface WebSocketEvent {
  type: 'incident.new' | 'incident.updated' | 'alert.sent' | 'billing.updated' | 'connected';
  data: Record<string, unknown>;
  timestamp?: string;
}

export type WsStatus = 'connecting' | 'connected' | 'disconnected';

/** Derive WS URL from env or auto-detect from current page location. */
function getWsUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  if (typeof window === 'undefined') return 'ws://localhost:8001';
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}`;
}

const MAX_BACKOFF_MS = 30_000;
const AUTH_CLOSE_CODE = 4001;

export function useWebSocket() {
  const { isAuthenticated } = useAuth();
  const [status, setStatus] = useState<WsStatus>('disconnected');
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const cleanup = useCallback(() => {
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

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const token = localStorage.getItem('accessToken');
    if (!token) {
      setStatus('disconnected');
      return;
    }

    cleanup();
    setStatus('connecting');

    const ws = new WebSocket(`${getWsUrl()}/ws/events?token=${token}`);
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
        if (mountedRef.current) connect();
      }, delay);
    };

    ws.onerror = () => {
      // onclose will fire after this — reconnect handled there
    };
  }, [cleanup]);

  useEffect(() => {
    mountedRef.current = true;

    if (isAuthenticated) {
      connect();
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
