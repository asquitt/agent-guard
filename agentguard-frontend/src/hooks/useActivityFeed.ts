'use client';

import { useCallback, useSyncExternalStore } from 'react';
import type { WebSocketEvent } from '@/hooks/useWebSocket';

export interface ActivityItem {
  id: string;
  type: WebSocketEvent['type'];
  title: string;
  description?: string;
  severity?: string;
  timestamp: string;
}

const MAX_ITEMS = 50;
let nextId = 0;

/** Lightweight external store for activity events (no re-render storms). */
function createActivityStore() {
  let items: ActivityItem[] = [];
  const listeners = new Set<() => void>();

  function getSnapshot() {
    return items;
  }

  function subscribe(listener: () => void) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  function push(item: Omit<ActivityItem, 'id'>) {
    const newItem: ActivityItem = { ...item, id: String(++nextId) };
    items = [newItem, ...items].slice(0, MAX_ITEMS);
    listeners.forEach((l) => l());
  }

  function clear() {
    items = [];
    listeners.forEach((l) => l());
  }

  return { getSnapshot, subscribe, push, clear };
}

// Singleton store — shared across all consumers
const store = createActivityStore();

/** Format a WebSocket event into an ActivityItem */
export function pushWsEvent(event: WebSocketEvent) {
  if (event.type === 'connected') return;

  const data = event.data ?? {};
  const timestamp = event.timestamp ?? new Date().toISOString();

  switch (event.type) {
    case 'incident.new':
      store.push({
        type: event.type,
        title: 'New incident detected',
        description: (data.title as string) ?? (data.category as string) ?? undefined,
        severity: data.severity as string | undefined,
        timestamp,
      });
      break;
    case 'incident.updated':
      store.push({
        type: event.type,
        title: 'Incident updated',
        description: (data.title as string) ?? `Status → ${data.status ?? 'unknown'}`,
        severity: data.severity as string | undefined,
        timestamp,
      });
      break;
    case 'alert.sent':
      store.push({
        type: event.type,
        title: 'Alert sent',
        description: (data.destination_name as string) ?? (data.channel as string) ?? undefined,
        timestamp,
      });
      break;
    case 'billing.updated':
      store.push({
        type: event.type,
        title: 'Billing updated',
        timestamp,
      });
      break;
    default: {
      // Future-proof: handle unknown event types
      const unknownType = String(event.type);
      store.push({
        type: 'connected',
        title: unknownType.replace(/\./g, ' '),
        timestamp,
      });
    }
  }
}

/** Hook to consume the activity feed. */
export function useActivityFeed() {
  const items = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
  const clearFeed = useCallback(() => store.clear(), []);
  return { items, clearFeed };
}
