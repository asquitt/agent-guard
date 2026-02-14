'use client';

import { X } from 'lucide-react';
import type { IncidentFilters } from '@/types';

const FILTER_LABELS: Record<string, string> = {
  status: 'Status',
  severity: 'Severity',
  category: 'Category',
  q: 'Search',
  dateFrom: 'From',
  dateTo: 'To',
  detectorId: 'Detector',
};

// Keys that are user-facing filters (exclude pagination, sort, internal keys)
const CHIP_KEYS = ['status', 'severity', 'category', 'q', 'dateFrom', 'dateTo', 'detectorId'];

export function ActiveFilterChips({
  filters,
  onClear,
  onClearAll,
}: {
  filters: IncidentFilters;
  onClear: (key: keyof IncidentFilters & string, value: undefined) => void;
  onClearAll: () => void;
}) {
  const chips = CHIP_KEYS
    .filter((key) => {
      const val = filters[key as keyof IncidentFilters];
      return val !== undefined && val !== '';
    })
    .map((key) => ({
      key,
      label: FILTER_LABELS[key] ?? key,
      value: String(filters[key as keyof IncidentFilters]),
    }));

  if (chips.length === 0) return null;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      {chips.map((chip) => (
        <span
          key={chip.key}
          className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
        >
          {chip.label}: {chip.value}
          <button
            onClick={() => onClear(chip.key as keyof IncidentFilters & string, undefined)}
            className="ml-0.5 rounded-full p-0.5 hover:bg-primary/20 transition-colors"
            aria-label={`Remove ${chip.label} filter`}
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      {chips.length > 1 && (
        <button
          onClick={onClearAll}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
