import { AlertTriangle } from 'lucide-react';

interface QueryErrorProps {
  message?: string;
  onRetry?: () => void;
}

/**
 * Reusable error state for failed TanStack queries.
 * Renders a bordered card with an alert icon, message, and optional retry button.
 */
export function QueryError({
  message = 'Something went wrong. Please try again.',
  onRetry,
}: QueryErrorProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5 py-12 text-center">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10">
        <AlertTriangle className="h-5 w-5 text-red-400" />
      </div>
      <p className="text-sm font-medium text-foreground">Failed to load data</p>
      <p className="mt-1 max-w-sm text-xs text-muted-foreground">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 rounded-lg border border-border px-4 py-1.5 text-xs font-medium text-foreground hover:bg-muted/50"
        >
          Try again
        </button>
      )}
    </div>
  );
}
