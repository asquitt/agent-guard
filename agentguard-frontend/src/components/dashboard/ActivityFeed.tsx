'use client';

import { clsx } from 'clsx';
import { useActivityFeed, type ActivityItem } from '@/hooks/useActivityFeed';
import { timeAgo } from '@/lib/format';
import { Activity, AlertTriangle, Bell, CreditCard, ShieldAlert, RefreshCw } from 'lucide-react';

const EVENT_ICONS: Record<string, typeof Activity> = {
  'incident.new': ShieldAlert,
  'incident.updated': RefreshCw,
  'alert.sent': Bell,
  'billing.updated': CreditCard,
};

const EVENT_COLORS: Record<string, string> = {
  'incident.new': 'text-red-500',
  'incident.updated': 'text-blue-500',
  'alert.sent': 'text-amber-500',
  'billing.updated': 'text-green-500',
};

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-green-500',
  info: 'bg-blue-400',
};

export function ActivityFeed({ className }: { className?: string }) {
  const { items, clearFeed } = useActivityFeed();

  return (
    <div className={clsx('rounded-xl border border-border bg-card', className)}>
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-foreground">Live Activity</h3>
          {items.length > 0 && (
            <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary/10 px-1.5 text-[10px] font-bold text-primary">
              {items.length}
            </span>
          )}
        </div>
        {items.length > 0 && (
          <button
            onClick={clearFeed}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      <div className="max-h-80 overflow-y-auto">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Activity className="mb-2 h-8 w-8 text-muted-foreground/30" />
            <p className="text-xs text-muted-foreground">No recent activity</p>
            <p className="text-[10px] text-muted-foreground/60">
              Events will appear here in real-time
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {items.map((item) => (
              <ActivityRow key={item.id} item={item} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function ActivityRow({ item }: { item: ActivityItem }) {
  const Icon = EVENT_ICONS[item.type] ?? Activity;
  const iconColor = EVENT_COLORS[item.type] ?? 'text-muted-foreground';

  return (
    <li className="flex items-start gap-3 px-4 py-2.5 transition-colors hover:bg-muted/30">
      <div className={clsx('mt-0.5 shrink-0', iconColor)}>
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <p className="text-xs font-medium text-foreground">{item.title}</p>
          {item.severity && (
            <span
              className={clsx(
                'inline-block h-1.5 w-1.5 rounded-full',
                SEVERITY_DOT[item.severity] ?? SEVERITY_DOT.info,
              )}
              title={item.severity}
            />
          )}
        </div>
        {item.description && (
          <p className="truncate text-[11px] text-muted-foreground">{item.description}</p>
        )}
      </div>
      <time
        className="shrink-0 text-[10px] text-muted-foreground/60"
        title={new Date(item.timestamp).toLocaleString()}
      >
        {timeAgo(item.timestamp)}
      </time>
    </li>
  );
}
