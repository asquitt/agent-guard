'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * Hook for J/K keyboard navigation through a list.
 * Listens for the `keyboard:list-nav` custom event dispatched by KeyboardShortcuts.
 *
 * @param count - Total number of items in the list
 * @param onSelect - Callback when Enter is pressed on the focused item
 * @returns focusedIndex (-1 when no item is focused), and a reset function
 */
export function useListKeyNav(
  count: number,
  onSelect?: (index: number) => void,
): { focusedIndex: number; resetFocus: () => void } {
  const [focusedIndex, setFocusedIndex] = useState(-1);

  useEffect(() => {
    function handleNav(e: Event) {
      const { direction } = (e as CustomEvent).detail ?? {};
      if (!direction || count === 0) return;

      setFocusedIndex((prev) => {
        if (direction === 'next') return Math.min(prev + 1, count - 1);
        if (direction === 'prev') return Math.max(prev - 1, 0);
        return prev;
      });
    }

    function handleKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === 'Enter') {
        setFocusedIndex((prev) => {
          if (prev >= 0 && prev < count && onSelect) onSelect(prev);
          return prev;
        });
      }
    }

    window.addEventListener('keyboard:list-nav', handleNav);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keyboard:list-nav', handleNav);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [count, onSelect]);

  // Reset when count changes (e.g. new page)
  useEffect(() => {
    setFocusedIndex(-1);
  }, [count]);

  const resetFocus = useCallback(() => setFocusedIndex(-1), []);

  return { focusedIndex, resetFocus };
}
