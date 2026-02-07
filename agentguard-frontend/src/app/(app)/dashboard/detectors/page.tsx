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
};

const MODE_COLORS: Record<string, string> = {
  MONITOR: 'bg-blue-50 text-blue-600',
  WARN: 'bg-warning-50 text-warning-600',
  REDACT: 'bg-orange-50 text-orange-600',
  BLOCK: 'bg-danger-50 text-danger-600',
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
        <h1 className="text-2xl font-bold text-gray-900">Detectors</h1>
        <p className="text-sm text-gray-500">
          Configure detection rules for your LLM traffic
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        </div>
      ) : detectors.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
          <p className="text-sm text-gray-500">No detectors configured yet</p>
          <p className="mt-1 text-xs text-gray-400">
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
    <div className="rounded-xl border border-gray-200 bg-white p-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900">
              {detector.name}
            </h3>
            <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
              {CATEGORY_LABELS[detector.category] ?? detector.category}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">
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
            detector.isActive ? 'bg-primary-600' : 'bg-gray-300',
          )}
        >
          <span
            className={clsx(
              'inline-block h-4 w-4 rounded-full bg-white transition-transform',
              detector.isActive ? 'translate-x-6' : 'translate-x-1',
            )}
          />
        </button>
      </div>

      {/* Action mode selector */}
      <div className="mt-4">
        <p className="mb-2 text-xs font-medium uppercase text-gray-500">
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
                  ? MODE_COLORS[mode] ?? 'bg-gray-100 text-gray-600'
                  : 'bg-gray-50 text-gray-400 hover:bg-gray-100 hover:text-gray-600',
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
          <p className="mb-1 text-xs font-medium uppercase text-gray-500">
            Configuration
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(detector.config).map(([key, val]) => (
              <span
                key={key}
                className="inline-flex rounded bg-gray-50 px-2 py-1 text-xs text-gray-600"
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
