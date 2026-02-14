'use client';

import { clsx } from 'clsx';
import { useTableDensity } from '@/hooks/useTableDensity';
import { AlignJustify, List } from 'lucide-react';

/**
 * Toggle button for switching between compact and comfortable table density.
 * Renders as a segmented button pair.
 */
export function DensityToggle({ className }: { className?: string }) {
  const { density, toggle } = useTableDensity();

  return (
    <div
      className={clsx('inline-flex rounded-lg border border-border', className)}
      role="radiogroup"
      aria-label="Table density"
    >
      <button
        onClick={density !== 'comfortable' ? toggle : undefined}
        className={clsx(
          'flex items-center gap-1 rounded-l-lg px-2 py-1.5 text-xs transition-colors',
          density === 'comfortable'
            ? 'bg-muted text-foreground'
            : 'text-muted-foreground hover:text-foreground',
        )}
        aria-label="Comfortable view"
        role="radio"
        aria-checked={density === 'comfortable'}
      >
        <AlignJustify className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={density !== 'compact' ? toggle : undefined}
        className={clsx(
          'flex items-center gap-1 rounded-r-lg px-2 py-1.5 text-xs transition-colors',
          density === 'compact'
            ? 'bg-muted text-foreground'
            : 'text-muted-foreground hover:text-foreground',
        )}
        aria-label="Compact view"
        role="radio"
        aria-checked={density === 'compact'}
      >
        <List className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
