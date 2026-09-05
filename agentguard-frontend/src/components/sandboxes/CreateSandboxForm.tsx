'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { createSandbox, listTemplates } from '@/lib/api/sandboxes';
import type { SandboxTemplate } from '@/lib/api/sandboxes';

const CAPABILITY_TYPES = [
  { value: 'file:read', label: 'File Read' },
  { value: 'file:write', label: 'File Write' },
  { value: 'network:http', label: 'HTTP Network' },
  { value: 'network:dns', label: 'DNS Lookup' },
  { value: 'api:call', label: 'API Call' },
  { value: 'tool:execute', label: 'Tool Execute' },
  { value: 'secret:access', label: 'Secret Access' },
];

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export default function CreateSandboxForm({ onClose, onSuccess }: Props) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [image, setImage] = useState('agentguard/sandbox-base:latest');
  const [memoryMb, setMemoryMb] = useState(256);
  const [maxTokens, setMaxTokens] = useState(10000);
  const [timeoutSeconds, setTimeoutSeconds] = useState(300);
  const [denyAllEgress, setDenyAllEgress] = useState(true);
  const [allowedHosts, setAllowedHosts] = useState('');

  // Environment variables
  const [envKey, setEnvKey] = useState('');
  const [envVal, setEnvVal] = useState('');
  const [envVars, setEnvVars] = useState<{ key: string; value: string }[]>([]);

  // Capabilities
  const [capType, setCapType] = useState(CAPABILITY_TYPES[0].value);
  const [capTarget, setCapTarget] = useState('');
  const [caps, setCaps] = useState<{ type: string; target: string }[]>([]);

  const { data: templates } = useQuery({ queryKey: ['sandbox-templates'], queryFn: listTemplates });
  const mutation = useMutation({ mutationFn: createSandbox, onSuccess });

  function applyTemplate(t: SandboxTemplate) {
    setImage(t.image);
    setCaps(t.capabilities.map((c) => ({ type: c.type, target: c.target })));
    setMemoryMb(t.resourceLimits.memory_mb);
    setMaxTokens(t.resourceLimits.max_tokens);
    setTimeoutSeconds(t.resourceLimits.timeout_seconds);
    setDenyAllEgress(t.networkPolicy.deny_all_egress);
    setAllowedHosts(t.networkPolicy.allowed_hosts.join('\n'));
  }

  function addEnvVar() {
    if (!envKey.trim()) return;
    setEnvVars((prev) => [...prev, { key: envKey.trim(), value: envVal }]);
    setEnvKey('');
    setEnvVal('');
  }

  function addCap() {
    if (!capTarget.trim()) return;
    setCaps((prev) => [...prev, { type: capType, target: capTarget.trim() }]);
    setCapTarget('');
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const environment: Record<string, string> = {};
    for (const ev of envVars) environment[ev.key] = ev.value;
    mutation.mutate({
      name: name.trim(),
      description: description || undefined,
      image,
      capabilities: caps,
      resource_limits: { memory_mb: memoryMb, max_tokens: maxTokens, timeout_seconds: timeoutSeconds },
      network_policy: {
        deny_all_egress: denyAllEgress,
        allowed_hosts: allowedHosts.split('\n').map((h) => h.trim()).filter(Boolean),
        allowed_ports: [443, 80],
      },
      environment: Object.keys(environment).length > 0 ? environment : undefined,
    });
  }

  const inputCls = 'w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground';

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h3 className="mb-4 text-sm font-semibold text-foreground">Create Sandbox</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Template Selector */}
        {templates && templates.length > 0 && (
          <fieldset>
            <legend className="mb-1 block text-xs text-muted-foreground">Start from Template</legend>
            <div className="flex flex-wrap gap-2">
              {templates.map((t) => (
                <button key={t.id} type="button" onClick={() => applyTemplate(t)} className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted/50">
                  {t.name}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        {/* Basic Info */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="sandbox-name" className="mb-1 block text-xs text-muted-foreground">Name *</label>
            <input id="sandbox-name" value={name} onChange={(e) => setName(e.target.value)} className={inputCls} placeholder="my-agent-sandbox" />
          </div>
          <div>
            <label htmlFor="sandbox-description" className="mb-1 block text-xs text-muted-foreground">Description</label>
            <input id="sandbox-description" value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} placeholder="Optional description" />
          </div>
          <div>
            <label htmlFor="sandbox-image" className="mb-1 block text-xs text-muted-foreground">Image</label>
            <input id="sandbox-image" value={image} onChange={(e) => setImage(e.target.value)} className={inputCls} placeholder="agentguard/sandbox-base:latest" />
          </div>
        </div>

        {/* Resource Limits */}
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor="sandbox-memory" className="mb-1 block text-xs text-muted-foreground">Memory (MB)</label>
            <input id="sandbox-memory" type="number" value={memoryMb} onChange={(e) => setMemoryMb(Number(e.target.value))} min={64} max={8192} className={inputCls} />
          </div>
          <div>
            <label htmlFor="sandbox-token-budget" className="mb-1 block text-xs text-muted-foreground">Token Budget</label>
            <input id="sandbox-token-budget" type="number" value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} min={100} className={inputCls} />
          </div>
          <div>
            <label htmlFor="sandbox-timeout" className="mb-1 block text-xs text-muted-foreground">Timeout (s)</label>
            <input id="sandbox-timeout" type="number" value={timeoutSeconds} onChange={(e) => setTimeoutSeconds(Number(e.target.value))} min={10} className={inputCls} />
          </div>
        </div>

        {/* Network */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
            <input type="checkbox" checked={denyAllEgress} onChange={(e) => setDenyAllEgress(e.target.checked)} className="rounded" />
            Deny all egress (whitelist only)
          </label>
          <textarea aria-label="Allowed egress hosts" value={allowedHosts} onChange={(e) => setAllowedHosts(e.target.value)} rows={2} className={`mt-2 ${inputCls}`} placeholder="Allowed hosts (one per line)" />
        </div>

        {/* Capabilities */}
        <fieldset>
          <legend className="mb-1 block text-xs text-muted-foreground">Capabilities</legend>
          <div className="flex gap-2">
            <select aria-label="Capability type" value={capType} onChange={(e) => setCapType(e.target.value)} className="rounded-lg border border-border bg-background px-2 py-2 text-sm">
              {CAPABILITY_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <input aria-label="Capability target" value={capTarget} onChange={(e) => setCapTarget(e.target.value)} className={`flex-1 ${inputCls}`} placeholder="Target (e.g. *.openai.com)" />
            <button type="button" onClick={addCap} className="rounded-lg bg-muted px-3 py-2 text-xs font-medium text-foreground hover:bg-muted/80">Add</button>
          </div>
          {caps.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {caps.map((c, i) => (
                <span key={i} className="inline-flex items-center gap-1 rounded bg-blue-500/10 px-2 py-1 text-xs text-blue-400">
                  {c.type}: {c.target}
                  <button type="button" aria-label={`Remove ${c.type} capability`} onClick={() => setCaps((p) => p.filter((_, j) => j !== i))} className="ml-1 text-blue-300 hover:text-white">&times;</button>
                </span>
              ))}
            </div>
          )}
        </fieldset>

        {/* Env Vars */}
        <fieldset>
          <legend className="mb-1 block text-xs text-muted-foreground">Environment Variables</legend>
          <div className="flex gap-2">
            <input aria-label="Environment variable name" value={envKey} onChange={(e) => setEnvKey(e.target.value)} className={`flex-1 ${inputCls}`} placeholder="KEY" />
            <input aria-label="Environment variable value" value={envVal} onChange={(e) => setEnvVal(e.target.value)} className={`flex-1 ${inputCls}`} placeholder="value" />
            <button type="button" onClick={addEnvVar} className="rounded-lg bg-muted px-3 py-2 text-xs font-medium text-foreground hover:bg-muted/80">Add</button>
          </div>
          {envVars.length > 0 && (
            <div className="mt-2 space-y-1">
              {envVars.map((ev, i) => (
                <div key={i} className="flex items-center justify-between rounded bg-muted/50 px-2 py-1 text-xs">
                  <span className="font-mono text-foreground">{ev.key}=••••••</span>
                  <button type="button" aria-label={`Remove ${ev.key} environment variable`} onClick={() => setEnvVars((p) => p.filter((_, j) => j !== i))} className="text-red-400 hover:text-red-300">&times;</button>
                </div>
              ))}
            </div>
          )}
        </fieldset>

        {/* Submit */}
        <div className="flex gap-2">
          <button type="submit" disabled={!name.trim() || mutation.isPending} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50">
            {mutation.isPending ? 'Creating...' : 'Create'}
          </button>
          <button type="button" onClick={onClose} className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
