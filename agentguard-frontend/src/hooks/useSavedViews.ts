'use client';

import { useCallback, useSyncExternalStore } from 'react';

export interface SavedView {
  id: string;
  name: string;
  filters: Record<string, string | number | undefined>;
  createdAt: string;
}

const STORAGE_KEY = 'agentguard:saved-views';
const listeners = new Set<() => void>();
let cache: SavedView[] | null = null;

function load(): SavedView[] {
  if (cache) return cache;
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    cache = raw ? (JSON.parse(raw) as SavedView[]) : [];
  } catch {
    cache = [];
  }
  return cache;
}

function persist(views: SavedView[]) {
  cache = views;
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(views));
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Hook for managing saved filter views (persisted in localStorage).
 * Each view stores a snapshot of the current filter state.
 */
export function useSavedViews(scope: string = 'incidents') {
  const allViews = useSyncExternalStore(subscribe, load, () => []);
  const views = allViews.filter((v) => v.id.startsWith(`${scope}:`));

  const save = useCallback(
    (name: string, filters: Record<string, string | number | undefined>) => {
      const id = `${scope}:${Date.now()}`;
      const view: SavedView = {
        id,
        name,
        filters: { ...filters },
        createdAt: new Date().toISOString(),
      };
      persist([...load(), view]);
    },
    [scope],
  );

  const remove = useCallback((id: string) => {
    persist(load().filter((v) => v.id !== id));
  }, []);

  return { views, save, remove };
}
