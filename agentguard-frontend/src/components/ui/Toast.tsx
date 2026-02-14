'use client';

import { useEffect } from 'react';
import { clsx } from 'clsx';

const BORDER_COLORS: Record<string, string> = {
  critical: 'border-l-red-600',
  high: 'border-l-orange-500',
  medium: 'border-l-yellow-500',
  low: 'border-l-blue-400',
  info: 'border-l-gray-400',
};

const BG_COLORS: Record<string, string> = {
  critical: 'bg-red-50',
  high: 'bg-orange-50',
  medium: 'bg-yellow-50',
  low: 'bg-blue-50',
  info: 'bg-muted/50',
};

export interface ToastItem {
  id: string;
  message: string;
  severity: string;
}

export function Toast({
  message,
  severity,
  onDismiss,
}: {
  message: string;
  severity: string;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      role="alert"
      aria-live="polite"
      className={clsx(
        'flex items-start gap-3 rounded-lg border-l-4 px-4 py-3 shadow-lg',
        BORDER_COLORS[severity] ?? 'border-l-gray-400',
        BG_COLORS[severity] ?? 'bg-muted/50',
      )}
    >
      <div className="flex-1">
        <p className="text-sm font-medium text-foreground">{message}</p>
      </div>
      <button
        onClick={onDismiss}
        className="text-muted-foreground/60 hover:text-muted-foreground"
        aria-label="Dismiss"
      >
        &times;
      </button>
    </div>
  );
}
