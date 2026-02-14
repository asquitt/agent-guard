import { clsx } from 'clsx';

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ className, style }: SkeletonProps) {
  return (
    <div
      className={clsx(
        'animate-pulse rounded-md bg-muted',
        className,
      )}
      style={style}
    />
  );
}

/** 4 metric cards matching dashboard layout */
export function DashboardSkeleton() {
  return (
    <div>
      {/* Metric cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-5">
            <Skeleton className="mb-2 h-4 w-24" />
            <Skeleton className="h-8 w-16" />
          </div>
        ))}
      </div>

      {/* Recent incidents table */}
      <div className="mt-8 rounded-xl border border-border bg-card">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <Skeleton className="h-5 w-36" />
          <Skeleton className="h-4 w-16" />
        </div>
        <div className="divide-y divide-border">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-6 py-3">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="ml-auto h-4 w-32" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Table skeleton for incidents, traces, etc. */
export function TableSkeleton({ rows = 8, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="divide-y divide-border">
      {/* Header */}
      <div className="flex items-center gap-4 px-4 py-3">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-20" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-3">
          {Array.from({ length: cols }).map((_, j) => (
            <Skeleton
              key={j}
              className={clsx(
                'h-4',
                j === 0 ? 'w-40' : j === cols - 1 ? 'w-28' : 'w-20',
              )}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Summary cards + chart placeholder for analytics */
export function AnalyticsSkeleton() {
  return (
    <div>
      {/* Summary cards */}
      <div className="mb-6 grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-4">
            <Skeleton className="mb-2 h-3 w-20" />
            <Skeleton className="h-7 w-16" />
          </div>
        ))}
      </div>

      {/* Chart placeholder */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex h-48 items-end gap-1">
          {Array.from({ length: 20 }).map((_, i) => (
            <Skeleton
              key={i}
              className="flex-1"
              style={{ height: `${20 + Math.random() * 60}%` }}
            />
          ))}
        </div>
        <div className="mt-2 flex justify-between">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-16" />
        </div>
      </div>
    </div>
  );
}
