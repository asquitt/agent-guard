import type { LucideIcon } from 'lucide-react';
import Link from 'next/link';

interface EmptyStateHint {
  label: string;
  href: string;
}

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  /** Contextual links shown below the description. */
  hints?: EmptyStateHint[];
}

export function EmptyState({ icon: Icon, title, description, action, hints }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-card py-16 text-center">
      {Icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Icon className="h-6 w-6 text-muted-foreground" />
        </div>
      )}
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">{description}</p>
      )}
      {hints && hints.length > 0 && (
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          {hints.map((h) => (
            <Link
              key={h.href}
              href={h.href}
              className="rounded-full border border-border px-3 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary"
            >
              {h.label} →
            </Link>
          ))}
        </div>
      )}
      {action && (
        <div className="mt-4">
          {action.href ? (
            <Link
              href={action.href}
              className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90"
            >
              {action.label}
            </Link>
          ) : (
            <button
              onClick={action.onClick}
              className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90"
            >
              {action.label}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
