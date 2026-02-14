'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { addCapability, removeCapability } from '@/lib/api/sandboxes';
import type { SandboxCapability } from '@/types/sandbox';

const CAPABILITY_TYPES = [
  { value: 'file:read', label: 'File Read' },
  { value: 'file:write', label: 'File Write' },
  { value: 'network:http', label: 'HTTP Network' },
  { value: 'network:dns', label: 'DNS Lookup' },
  { value: 'api:call', label: 'API Call' },
  { value: 'tool:execute', label: 'Tool Execute' },
  { value: 'secret:access', label: 'Secret Access' },
];

const CAPABILITY_LABELS: Record<string, string> = Object.fromEntries(
  CAPABILITY_TYPES.map((t) => [t.value, t.label]),
);

interface Props {
  sandboxId: string;
  capabilities: SandboxCapability[];
}

export default function CapabilityManager({ sandboxId, capabilities }: Props) {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [capType, setCapType] = useState(CAPABILITY_TYPES[0].value);
  const [capTarget, setCapTarget] = useState('');

  const addMut = useMutation({
    mutationFn: (cap: { type: string; target: string }) => addCapability(sandboxId, cap),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sandboxes', sandboxId] });
      setCapTarget('');
      setShowAdd(false);
    },
  });

  const removeMut = useMutation({
    mutationFn: (index: number) => removeCapability(sandboxId, index),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sandboxes', sandboxId] }),
  });

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">
          Capabilities ({capabilities.length})
        </h3>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted/50"
        >
          {showAdd ? 'Cancel' : 'Add Capability'}
        </button>
      </div>

      {showAdd && (
        <div className="border-b border-border px-4 py-3">
          <div className="flex gap-2">
            <select
              value={capType}
              onChange={(e) => setCapType(e.target.value)}
              className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm"
            >
              {CAPABILITY_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <input
              value={capTarget}
              onChange={(e) => setCapTarget(e.target.value)}
              placeholder="Target (e.g. *.openai.com)"
              className="flex-1 rounded-lg border border-border bg-background px-3 py-1.5 text-sm text-foreground"
            />
            <button
              onClick={() => addMut.mutate({ type: capType, target: capTarget.trim() })}
              disabled={!capTarget.trim() || addMut.isPending}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary/80 disabled:opacity-50"
            >
              {addMut.isPending ? 'Adding...' : 'Add'}
            </button>
          </div>
        </div>
      )}

      {capabilities.length > 0 ? (
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Type</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Target</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Expires</th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {capabilities.map((cap, i) => (
              <tr key={i} className="hover:bg-muted/50">
                <td className="px-4 py-3">
                  <span className="inline-flex rounded bg-blue-500/10 px-2 py-0.5 text-xs font-medium text-blue-400">
                    {CAPABILITY_LABELS[cap.type] ?? cap.type}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-sm text-foreground">{cap.target}</td>
                <td className="px-4 py-3 text-sm text-muted-foreground">
                  {cap.expires_at ? new Date(cap.expires_at).toLocaleString() : 'Never'}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => removeMut.mutate(i)}
                    disabled={removeMut.isPending}
                    className="rounded px-2 py-1 text-xs text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="p-8 text-center text-muted-foreground">
          No capabilities granted. This sandbox has no permissions (default-deny).
        </div>
      )}
    </div>
  );
}
