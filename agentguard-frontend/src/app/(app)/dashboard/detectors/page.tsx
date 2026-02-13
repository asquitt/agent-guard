'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { listDetectors, updateDetector } from '@/lib/api';
import type { Detector } from '@/types';

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

const MODE_COLORS: Record<string, string> = {
  MONITOR: 'bg-blue-50 text-blue-600',
  WARN: 'bg-yellow-500/10 text-yellow-400',
  REDACT: 'bg-orange-50 text-orange-600',
  BLOCK: 'bg-red-500/10 text-red-400',
};

export default function DetectorsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['detectors'],
    queryFn: () => listDetectors(),
  });

  const detectors = data?.items ?? [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Detectors</h1>
        <p className="text-sm text-muted-foreground">
          Configure detection rules for your LLM traffic
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : detectors.length === 0 ? (
        <div className="rounded-xl border border-border bg-card py-16 text-center">
          <p className="text-sm text-muted-foreground">No detectors configured yet</p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            Detectors are created automatically when you first proxy a request
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {detectors.map((d) => (
            <DetectorCard key={d.id} detector={d} />
          ))}
        </div>
      )}
    </div>
  );
}

function DetectorCard({ detector }: { detector: Detector }) {
  const queryClient = useQueryClient();

  const toggleMutation = useMutation({
    mutationFn: (active: boolean) =>
      updateDetector(detector.id, { is_active: active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['detectors'] }),
  });

  const modeMutation = useMutation({
    mutationFn: (mode: string) =>
      updateDetector(detector.id, { action_mode: mode }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['detectors'] }),
  });

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-start justify-between">
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

        {/* Toggle */}
        <button
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
      <div className="mt-4">
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
        <div className="mt-4">
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
