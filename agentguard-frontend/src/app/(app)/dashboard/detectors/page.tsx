'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { listDetectors, updateDetector } from '@/lib/api';
import type { Detector } from '@/types';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { QueryError } from '@/components/ui/QueryError';
import { Radar, X } from 'lucide-react';
import { useToast } from '@/hooks/useToast';

const ACTION_MODES = ['MONITOR', 'WARN', 'REDACT', 'BLOCK'] as const;

const CATEGORY_LABELS: Record<string, string> = {
  hallucination: 'Hallucination',
  pii_leak: 'PII Leak',
  compliance: 'Compliance',
  cost_anomaly: 'Cost Anomaly',
  loop: 'Loop Detection',
  prompt_injection: 'Prompt Injection',
  prompt_extraction: 'Prompt Extraction',
  toxicity: 'Toxicity & Bias',
  tool_call: 'Tool Call Validation',
  mcp_security: 'MCP Security',
};

import { MODE_COLORS } from '@/lib/constants';

export default function DetectorsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['detectors'],
    queryFn: () => listDetectors(),
  });

  const detectors = data?.items ?? [];
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggleOne = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelected((prev) =>
      prev.size === detectors.length
        ? new Set()
        : new Set(detectors.map((d) => d.id)),
    );
  }, [detectors]);

  const clearSelection = useCallback(() => setSelected(new Set()), []);

  // Bulk operations — fire parallel PATCH calls
  const bulkMutation = useMutation({
    mutationFn: async (update: { is_active?: boolean; action_mode?: string }) => {
      const ids = Array.from(selected);
      const results = await Promise.allSettled(
        ids.map((id) => updateDetector(id, update)),
      );
      const failed = results.filter((r) => r.status === 'rejected').length;
      return { total: ids.length, failed };
    },
    onSuccess: ({ total, failed }) => {
      queryClient.invalidateQueries({ queryKey: ['detectors'] });
      if (failed === 0) {
        toast.success(`Updated ${total} detector${total !== 1 ? 's' : ''}`);
      } else {
        toast.error(`${failed} of ${total} updates failed`);
      }
      clearSelection();
    },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Detectors</h1>
        <p className="text-sm text-muted-foreground">
          Configure detection rules for your LLM traffic
        </p>
      </div>

      {isError ? (
        <QueryError message="Failed to load detectors." onRetry={refetch} />
      ) : isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border bg-card p-6">
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <Skeleton className="h-5 w-36" />
                  <Skeleton className="h-4 w-48" />
                </div>
                <Skeleton className="h-6 w-11 rounded-full" />
              </div>
              <div className="mt-4 flex gap-2">
                {Array.from({ length: 4 }).map((_, j) => (
                  <Skeleton key={j} className="h-8 w-20 rounded-lg" />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : detectors.length === 0 ? (
        <EmptyState
          icon={Radar}
          title="No detectors configured"
          description="Detectors are created automatically when you first proxy a request through AgentGuard."
          hints={[
            { label: 'Create an API key', href: '/dashboard/api-keys' },
            { label: 'View integration docs', href: '/docs' },
          ]}
        />
      ) : (
        <>
          {/* Select all */}
          <div className="mb-3 flex items-center gap-3">
            <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={selected.size === detectors.length && detectors.length > 0}
                onChange={toggleAll}
                className="h-3.5 w-3.5 rounded border-border accent-primary"
              />
              Select all ({detectors.length})
            </label>
            {selected.size > 0 && (
              <span className="text-xs text-muted-foreground">
                {selected.size} selected
              </span>
            )}
          </div>

          <div className="space-y-4">
            {detectors.map((d) => (
              <DetectorCard
                key={d.id}
                detector={d}
                selected={selected.has(d.id)}
                onToggleSelect={() => toggleOne(d.id)}
              />
            ))}
          </div>

          {/* Bulk action bar */}
          {selected.size > 0 && (
            <BulkActionBar
              count={selected.size}
              loading={bulkMutation.isPending}
              onSetMode={(mode) => bulkMutation.mutate({ action_mode: mode })}
              onEnable={() => bulkMutation.mutate({ is_active: true })}
              onDisable={() => bulkMutation.mutate({ is_active: false })}
              onClear={clearSelection}
            />
          )}
        </>
      )}
    </div>
  );
}

function DetectorCard({
  detector,
  selected,
  onToggleSelect,
}: {
  detector: Detector;
  selected: boolean;
  onToggleSelect: () => void;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();

  const toggleMutation = useMutation({
    mutationFn: (active: boolean) =>
      updateDetector(detector.id, { is_active: active }),
    onSuccess: (_data, active) => {
      queryClient.invalidateQueries({ queryKey: ['detectors'] });
      toast.success(`${detector.name} ${active ? 'enabled' : 'disabled'}`);
    },
  });

  const modeMutation = useMutation({
    mutationFn: (mode: string) =>
      updateDetector(detector.id, { action_mode: mode }),
    onSuccess: (_data, mode) => {
      queryClient.invalidateQueries({ queryKey: ['detectors'] });
      toast.success(`${detector.name} set to ${mode.toLowerCase()}`);
    },
  });

  return (
    <div
      className={clsx(
        'rounded-xl border bg-card p-6 transition-colors',
        selected ? 'border-primary/50 bg-primary/5' : 'border-border',
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggleSelect}
            className="mt-1.5 h-3.5 w-3.5 rounded border-border accent-primary"
            aria-label={`Select ${detector.name}`}
          />
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-foreground">
                {detector.name}
              </h3>
              <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                {CATEGORY_LABELS[detector.category] ?? detector.category}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {detector.rules.length} rule{detector.rules.length !== 1 ? 's' : ''}
              {' · '}Created {new Date(detector.createdAt).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Toggle */}
        <button
          role="switch"
          aria-checked={detector.isActive}
          aria-label={`Toggle ${detector.name} detector`}
          onClick={() => toggleMutation.mutate(!detector.isActive)}
          disabled={toggleMutation.isPending}
          className={clsx(
            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
            detector.isActive ? 'bg-primary' : 'bg-muted',
          )}
        >
          <span
            className={clsx(
              'inline-block h-4 w-4 rounded-full bg-card transition-transform',
              detector.isActive ? 'translate-x-6' : 'translate-x-1',
            )}
          />
        </button>
      </div>

      {/* Action mode selector */}
      <div className="mt-4 ml-6.5">
        <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">
          Action Mode
        </p>
        <div className="flex gap-2">
          {ACTION_MODES.map((mode) => (
            <button
              key={mode}
              onClick={() => modeMutation.mutate(mode)}
              disabled={modeMutation.isPending}
              className={clsx(
                'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                detector.actionMode === mode
                  ? MODE_COLORS[mode] ?? 'bg-muted text-muted-foreground'
                  : 'bg-muted/50 text-muted-foreground/60 hover:bg-muted hover:text-muted-foreground',
              )}
            >
              {mode.toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Config summary */}
      {Object.keys(detector.config).length > 0 && (
        <div className="mt-4 ml-6.5">
          <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">
            Configuration
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(detector.config).map(([key, val]) => (
              <span
                key={key}
                className="inline-flex rounded bg-muted/50 px-2 py-1 text-xs text-muted-foreground"
              >
                {key}: {String(val)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** Floating bar with bulk actions for selected detectors. */
function BulkActionBar({
  count,
  loading,
  onSetMode,
  onEnable,
  onDisable,
  onClear,
}: {
  count: number;
  loading: boolean;
  onSetMode: (mode: string) => void;
  onEnable: () => void;
  onDisable: () => void;
  onClear: () => void;
}) {
  return (
    <div className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-2xl">
      <span className="text-xs font-medium text-foreground">
        {count} selected
      </span>
      <div className="h-4 w-px bg-border" />
      <div className="flex gap-1.5">
        {ACTION_MODES.map((mode) => (
          <button
            key={mode}
            onClick={() => onSetMode(mode)}
            disabled={loading}
            className={clsx(
              'rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50',
              MODE_COLORS[mode] ?? 'bg-muted text-muted-foreground',
            )}
          >
            {mode.toLowerCase()}
          </button>
        ))}
      </div>
      <div className="h-4 w-px bg-border" />
      <button
        onClick={onEnable}
        disabled={loading}
        className="rounded-md bg-green-500/10 px-2.5 py-1 text-xs font-medium text-green-400 transition-colors hover:bg-green-500/20 disabled:opacity-50"
      >
        Enable
      </button>
      <button
        onClick={onDisable}
        disabled={loading}
        className="rounded-md bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-400 transition-colors hover:bg-red-500/20 disabled:opacity-50"
      >
        Disable
      </button>
      <div className="h-4 w-px bg-border" />
      <button
        onClick={onClear}
        disabled={loading}
        className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
        aria-label="Clear selection"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
