'use client';

import { useCallback, useEffect, useState } from 'react';
import { clsx } from 'clsx';
import { healthUrl } from '@/lib/api/url';

interface ComponentStatus {
  name: string;
  status: string;
  response_time_ms?: number;
  message?: string;
}

interface HealthData {
  status: string;
  components: ComponentStatus[];
}

const COMPONENT_LABELS: Record<string, string> = {
  database: 'Database connectivity',
  redis: 'Redis connectivity',
  celery: 'Background worker reachability',
};

const STATUS_CONFIG: Record<string, { label: string; color: string; dotColor: string }> = {
  ok: { label: 'Observed healthy', color: 'text-green-600 dark:text-green-400', dotColor: 'bg-green-500' },
  degraded: { label: 'Observed degraded', color: 'text-yellow-600 dark:text-yellow-400', dotColor: 'bg-yellow-500' },
  error: { label: 'Observed error', color: 'text-red-600 dark:text-red-400', dotColor: 'bg-red-500' },
  unknown: { label: 'Unknown', color: 'text-muted-foreground', dotColor: 'bg-zinc-500' },
};

const OVERALL_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  healthy: { label: 'Configured checks passed', bg: 'bg-green-500/10 border-green-500/20', text: 'text-green-600 dark:text-green-400' },
  degraded: { label: 'Configured checks are degraded', bg: 'bg-yellow-500/10 border-yellow-500/20', text: 'text-yellow-600 dark:text-yellow-400' },
  unhealthy: { label: 'A configured check reported an error', bg: 'bg-red-500/10 border-red-500/20', text: 'text-red-600 dark:text-red-400' },
};

function isHealthData(value: unknown): value is HealthData {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<HealthData>;
  return typeof candidate.status === 'string' && Array.isArray(candidate.components);
}

export default function StatusPage() {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const response = await fetch(healthUrl('/detailed'), { cache: 'no-store' });
      const json: unknown = await response.json();
      if (!isHealthData(json)) {
        throw new Error('The configured health endpoint returned an unexpected response');
      }
      setData(json);
      setError('');
    } catch {
      setData(null);
      setError(
        'The configured health endpoint could not be reached or returned an unreadable response.',
      );
    } finally {
      setLastChecked(new Date());
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchHealth();
    const interval = window.setInterval(() => void fetchHealth(), 30_000);
    return () => window.clearInterval(interval);
  }, [fetchHealth]);

  const overallConfig = data ? OVERALL_CONFIG[data.status] : undefined;

  return (
    <div className="min-h-screen bg-muted/50">
      <div className="mx-auto max-w-2xl px-4 py-12">
        <div className="mb-8 text-center">
          <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-primary">
            Archived standalone project
          </p>
          <h1 className="text-3xl font-bold text-foreground">Configured Deployment Health</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            AgentGuard is mothballed as a standalone product. This page can
            report only the health of the explicitly configured archive process;
            it does not represent a public service.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            A point-in-time snapshot from this application&apos;s configured API health endpoint.
            It is not a public uptime history or service-level commitment.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16" aria-label="Loading health checks">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : (
          <>
            {data && overallConfig ? (
              <div className={clsx('mb-8 rounded-xl border p-6 text-center', overallConfig.bg)}>
                <p className={clsx('text-lg font-semibold', overallConfig.text)}>
                  {overallConfig.label}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  This covers only the components returned below.
                </p>
              </div>
            ) : (
              <div role="alert" className="mb-8 rounded-xl border border-zinc-500/30 bg-zinc-500/10 p-6 text-center">
                <p className="text-lg font-semibold text-foreground">Health state unknown</p>
                <p className="mt-2 text-sm text-muted-foreground">{error}</p>
              </div>
            )}

            {data && (
              <div className="rounded-xl border border-border bg-card">
                <div className="border-b border-border px-6 py-4">
                  <h2 className="text-sm font-semibold text-foreground">Returned component checks</h2>
                </div>
                {data.components.length > 0 ? (
                  <div className="divide-y divide-border">
                    {data.components.map((component) => (
                      <ComponentRow
                        key={component.name}
                        name={COMPONENT_LABELS[component.name] ?? component.name}
                        status={component.status}
                        responseTimeMs={component.response_time_ms}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="px-6 py-5 text-sm text-muted-foreground">
                    The endpoint returned no component checks.
                  </p>
                )}
              </div>
            )}

            <div className="mt-6 text-center">
              <button
                type="button"
                onClick={() => void fetchHealth()}
                className="text-sm text-primary hover:text-primary/80"
              >
                Refresh snapshot
              </button>
              {lastChecked && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Checked from this browser at {lastChecked.toLocaleTimeString()}
                </p>
              )}
            </div>
          </>
        )}

        <div className="mt-12 text-center text-xs leading-relaxed text-muted-foreground/70">
          This snapshot does not prove end-to-end proxy, provider, streaming,
          notification, deployment, or customer-traffic health.
        </div>
      </div>
    </div>
  );
}

function ComponentRow({
  name,
  status,
  responseTimeMs,
}: {
  name: string;
  status: string;
  responseTimeMs: number | undefined;
}) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.unknown;

  return (
    <div className="flex items-start justify-between gap-4 px-6 py-4">
      <div className="flex items-start gap-3">
        <div className={clsx('mt-1 h-2.5 w-2.5 shrink-0 rounded-full', config.dotColor)} />
        <div>
          <span className="text-sm font-medium text-foreground">{name}</span>
        </div>
      </div>
      <div className="shrink-0 text-right">
        <span className={clsx('text-sm font-medium', config.color)}>{config.label}</span>
        {responseTimeMs != null && (
          <p className="mt-1 text-xs text-muted-foreground">{responseTimeMs}ms check time</p>
        )}
      </div>
    </div>
  );
}
