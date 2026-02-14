'use client';

import { useCallback, useMemo } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';

/**
 * Sync filter state with URL search params so filtered views are
 * shareable, bookmarkable, and survive page refreshes.
 *
 * Usage:
 *   const { filters, setFilter } = useUrlFilters({
 *     defaults: { limit: 20, skip: 0 },
 *     numericKeys: ['skip', 'limit'],
 *   }) as { filters: MyFilters; setFilter: ... };
 */

type FilterValue = string | number | undefined;
type FilterRecord = Record<string, FilterValue>;

interface UseUrlFiltersOptions<K extends string = string> {
  /** Default values applied when a param is absent from the URL. */
  defaults?: Record<K, FilterValue>;
  /** Keys that should be parsed as numbers instead of strings. */
  numericKeys?: K[];
}

export function useUrlFilters<T extends FilterRecord = FilterRecord>(
  options: UseUrlFiltersOptions<string> = {},
) {
  const { defaults = {}, numericKeys = [] } = options;
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();

  const numericSet = useMemo(() => new Set(numericKeys), [numericKeys]);

  // Derive current filters from URL + defaults
  const filters = useMemo(() => {
    const result: FilterRecord = { ...defaults };
    searchParams.forEach((value, key) => {
      if (numericSet.has(key)) {
        const n = Number(value);
        result[key] = Number.isNaN(n) ? undefined : n;
      } else {
        result[key] = value;
      }
    });
    return result as T;
  }, [searchParams, defaults, numericSet]);

  // Build URLSearchParams from a filter object, omitting defaults & empty values
  const buildParams = useCallback(
    (next: FilterRecord) => {
      const params = new URLSearchParams();
      for (const [key, value] of Object.entries(next)) {
        if (value === undefined || value === '' || value === null) continue;
        // Omit if equal to default
        const def = defaults[key];
        if (def !== undefined && String(value) === String(def)) continue;
        params.set(key, String(value));
      }
      return params;
    },
    [defaults],
  );

  // Update a single filter key (resets skip to 0 unless the key is skip itself)
  const setFilter = useCallback(
    (key: keyof T & string, value: FilterValue) => {
      const next: FilterRecord = { ...filters };
      next[key] = value;
      // Reset pagination when changing filters (unless explicitly setting skip)
      if (key !== 'skip' && 'skip' in next) {
        next.skip = defaults.skip ?? 0;
      }
      const params = buildParams(next);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [filters, buildParams, pathname, router, defaults],
  );

  // Replace all filters at once
  const setFilters = useCallback(
    (next: Partial<T>) => {
      const merged: FilterRecord = { ...defaults, ...next };
      const params = buildParams(merged);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [buildParams, pathname, router, defaults],
  );

  // Reset to defaults (clear URL params)
  const resetFilters = useCallback(() => {
    router.replace(pathname, { scroll: false });
  }, [pathname, router]);

  return { filters, setFilter, setFilters, resetFilters };
}
