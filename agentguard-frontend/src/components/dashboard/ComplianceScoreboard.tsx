'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { clsx } from 'clsx';
import { getFrameworkScores } from '@/lib/api';
import type { FrameworkScore } from '@/types';

const PERIOD_OPTIONS = [
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
] as const;

const FRAMEWORK_COLORS: Record<string, string> = {
  'SOX': 'border-red-200 bg-red-50',
  'PCI-DSS': 'border-orange-200 bg-orange-50',
  'FFIEC': 'border-yellow-200 bg-yellow-50',
  'NYDFS-500': 'border-blue-200 bg-blue-50',
  'DORA': 'border-purple-200 bg-purple-50',
  'EU-AI-ACT': 'border-green-200 bg-green-50',
};

const FRAMEWORK_TEXT: Record<string, string> = {
  'SOX': 'text-red-700',
  'PCI-DSS': 'text-orange-700',
  'FFIEC': 'text-yellow-700',
  'NYDFS-500': 'text-blue-700',
  'DORA': 'text-purple-700',
  'EU-AI-ACT': 'text-green-700',
};

export function ComplianceScoreboard() {
  const [days, setDays] = useState(30);
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['compliance', 'framework-scores', days],
    queryFn: () => getFrameworkScores(days),
    refetchInterval: 60_000,
  });

  const frameworks = data?.frameworks ?? [];

  return (
    <div className="mb-8">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Framework Scoreboard</h2>
          <p className="text-xs text-muted-foreground">Violations by regulatory framework and requirement</p>
        </div>
        <div className="flex gap-1 rounded-lg border border-border bg-card p-0.5">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.days}
              onClick={() => setDays(opt.days)}
              className={clsx(
                'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                days === opt.days
                  ? 'bg-primary text-white'
                  : 'text-muted-foreground hover:bg-muted',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : frameworks.length === 0 ? (
        <div className="rounded-xl border border-border bg-card px-6 py-12 text-center">
          <p className="text-sm text-muted-foreground">No compliance violations detected</p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            Violations will appear here as compliance incidents are created
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {frameworks.map((fw) => (
            <FrameworkCard
              key={fw.name}
              framework={fw}
              isExpanded={expanded === fw.name}
              onToggle={() => setExpanded(expanded === fw.name ? null : fw.name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function FrameworkCard({
  framework,
  isExpanded,
  onToggle,
}: {
  framework: FrameworkScore;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const borderColor = FRAMEWORK_COLORS[framework.name] ?? 'border-border bg-muted/50';
  const textColor = FRAMEWORK_TEXT[framework.name] ?? 'text-foreground';

  return (
    <div
      className={clsx('cursor-pointer rounded-xl border-2 p-4 transition-shadow hover:shadow-md', borderColor)}
      onClick={onToggle}
    >
      <div className="flex items-center justify-between">
        <h3 className={clsx('text-sm font-semibold', textColor)}>{framework.name}</h3>
        <span className={clsx('text-2xl font-bold', textColor)}>
          {framework.totalViolations}
        </span>
      </div>
      <p className="mt-0.5 text-xs text-muted-foreground">
        {framework.requirements.length} requirement{framework.requirements.length !== 1 ? 's' : ''} violated
      </p>

      {isExpanded && framework.requirements.length > 0 && (
        <div className="mt-3 space-y-1.5 border-t border-border pt-3">
          {framework.requirements.map((req) => (
            <div key={req.name} className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{req.name}</span>
              <span className="ml-2 rounded-full bg-card px-2 py-0.5 text-xs font-medium text-foreground">
                {req.violationCount}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
