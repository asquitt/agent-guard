'use client';

import { useCallback, useSyncExternalStore } from 'react';

export type TableDensity = 'compact' | 'comfortable';

const STORAGE_KEY = 'agentguard:table-density';
const DEFAULT_DENSITY: TableDensity = 'comfortable';

let cachedDensity: TableDensity | null = null;
const listeners = new Set<() => void>();

function getDensity(): TableDensity {
  if (cachedDensity) return cachedDensity;
  if (typeof window === 'undefined') return DEFAULT_DENSITY;
  const stored = localStorage.getItem(STORAGE_KEY);
  cachedDensity = stored === 'compact' ? 'compact' : 'comfortable';
  return cachedDensity;
}

function setDensity(density: TableDensity) {
  cachedDensity = density;
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, density);
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Shared table density preference persisted in localStorage.
 * Returns the current density and a toggle function.
 */
export function useTableDensity() {
  const density = useSyncExternalStore(subscribe, getDensity, () => DEFAULT_DENSITY);

  const toggle = useCallback(() => {
    setDensity(density === 'compact' ? 'comfortable' : 'compact');
  }, [density]);

  return { density, toggle, isCompact: density === 'compact' };
}

/** CSS class helpers for table density */
export const DENSITY_CLASSES = {
  compact: {
    cell: 'px-3 py-1.5 text-xs',
    header: 'px-3 py-2 text-[10px]',
    row: 'hover:bg-muted/50',
  },
  comfortable: {
    cell: 'px-4 py-3 text-sm',
    header: 'px-4 py-3 text-xs',
    row: 'hover:bg-muted/50',
  },
} as const;
