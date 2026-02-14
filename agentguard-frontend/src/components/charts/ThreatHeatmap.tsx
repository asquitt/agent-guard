'use client';

import { useMemo } from 'react';
import { clsx } from 'clsx';

interface HeatmapBucket {
  bucket: string;
  incidents: number;
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

/**
 * 7×24 threat heatmap — maps incident count by day-of-week × hour-of-day.
 * Reveals attack pattern cadences at a glance.
 */
export function ThreatHeatmap({ data }: { data: HeatmapBucket[] }) {
  const { grid, maxValue } = useMemo(() => {
    // 7 rows (days) × 24 cols (hours)
    const g: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0));
    for (const b of data) {
      const d = new Date(b.bucket);
      if (isNaN(d.getTime())) continue;
      g[d.getDay()][d.getHours()] += b.incidents;
    }
    const max = Math.max(1, ...g.flat());
    return { grid: g, maxValue: max };
  }, [data]);

  function intensity(count: number): string {
    if (count === 0) return 'bg-muted/30';
    const ratio = count / maxValue;
    if (ratio > 0.75) return 'bg-red-500';
    if (ratio > 0.5) return 'bg-orange-500';
    if (ratio > 0.25) return 'bg-yellow-500';
    return 'bg-green-500/60';
  }

  return (
    <div>
      {/* Hour labels */}
      <div className="mb-1 flex items-end pl-10">
        {HOURS.map((h) => (
          <span
            key={h}
            className={clsx(
              'flex-1 text-center text-[9px] text-muted-foreground/60',
              h % 3 !== 0 && 'invisible',
            )}
          >
            {h.toString().padStart(2, '0')}
          </span>
        ))}
      </div>

      {/* Grid */}
      <div className="space-y-0.5">
        {DAYS.map((day, dayIdx) => (
          <div key={day} className="flex items-center gap-1.5">
            <span className="w-8 text-right text-[10px] font-medium text-muted-foreground">
              {day}
            </span>
            <div className="flex flex-1 gap-0.5">
              {HOURS.map((hour) => {
                const count = grid[dayIdx][hour];
                return (
                  <div
                    key={hour}
                    className={clsx(
                      'flex-1 rounded-[2px] transition-colors',
                      intensity(count),
                    )}
                    style={{ aspectRatio: '1' }}
                    title={`${day} ${hour.toString().padStart(2, '0')}:00 — ${count} incident${count !== 1 ? 's' : ''}`}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-2 flex items-center justify-end gap-1.5 text-[9px] text-muted-foreground">
        <span>Less</span>
        <div className="h-2.5 w-2.5 rounded-[2px] bg-muted/30" />
        <div className="h-2.5 w-2.5 rounded-[2px] bg-green-500/60" />
        <div className="h-2.5 w-2.5 rounded-[2px] bg-yellow-500" />
        <div className="h-2.5 w-2.5 rounded-[2px] bg-orange-500" />
        <div className="h-2.5 w-2.5 rounded-[2px] bg-red-500" />
        <span>More</span>
      </div>
    </div>
  );
}
