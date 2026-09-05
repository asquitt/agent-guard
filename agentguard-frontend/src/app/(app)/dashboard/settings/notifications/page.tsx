'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getNotificationPreferences, updateNotificationPreferences } from '@/lib/api';
import type { NotificationPreferences } from '@/lib/api';
import { useToast } from '@/hooks/useToast';

const ALL_CATEGORIES = [
  { value: 'hallucination', label: 'Hallucination' },
  { value: 'pii_leak', label: 'PII Leak' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'cost_anomaly', label: 'Cost Anomaly' },
  { value: 'loop', label: 'Loop Detection' },
  { value: 'prompt_injection', label: 'Prompt Injection' },
  { value: 'prompt_extraction', label: 'Prompt Extraction' },
  { value: 'toxicity', label: 'Toxicity & Bias' },
  { value: 'tool_call', label: 'Tool Call Validation' },
  { value: 'mcp_security', label: 'MCP Security' },
];

const DIGEST_OPTIONS = [
  { value: 'realtime', label: 'Real-time', desc: 'Immediately on each incident' },
  { value: 'hourly', label: 'Hourly', desc: 'Digest every hour' },
  { value: 'daily', label: 'Daily', desc: 'Digest once per day at 9 AM UTC' },
  { value: 'weekly', label: 'Weekly', desc: 'Digest every Monday at 9 AM UTC' },
  { value: 'off', label: 'Off', desc: 'No email notifications' },
] as const;

const SEVERITY_OPTIONS = [
  { value: 'info', label: 'Info & above', desc: 'All incidents' },
  { value: 'low', label: 'Low & above', desc: 'Skip info-level' },
  { value: 'medium', label: 'Medium & above', desc: 'Medium, high, critical' },
  { value: 'high', label: 'High & above', desc: 'High and critical only' },
  { value: 'critical', label: 'Critical only', desc: 'Only critical incidents' },
] as const;

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [dirty, setDirty] = useState(false);
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: getNotificationPreferences,
  });

  useEffect(() => {
    if (data && !prefs) setPrefs(data);
  }, [data, prefs]);

  const saveMutation = useMutation({
    mutationFn: updateNotificationPreferences,
    onSuccess: (saved) => {
      queryClient.setQueryData(['notification-preferences'], saved);
      setPrefs(saved);
      setDirty(false);
      toast.success('Preferences saved');
    },
  });

  function update(patch: Partial<NotificationPreferences>) {
    if (!prefs) return;
    setPrefs({ ...prefs, ...patch });
    setDirty(true);
  }

  function toggleCategory(cat: string) {
    if (!prefs) return;
    const cats = prefs.categories.includes(cat)
      ? prefs.categories.filter((c) => c !== cat)
      : [...prefs.categories, cat];
    update({ categories: cats });
  }

  if (isLoading || !prefs) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Notification Preferences</h1>
        <p className="text-sm text-muted-foreground">
          Control how and when you receive incident notifications
        </p>
      </div>

      {/* Email Notifications */}
      <Section title="Email Notifications">
        <Toggle
          label="Enable email notifications"
          checked={prefs.email_enabled}
          onChange={(v) => update({ email_enabled: v })}
        />
        {prefs.email_enabled && (
          <fieldset className="mt-4">
            <legend className="mb-2 block text-xs font-medium text-foreground">
              Digest Frequency
            </legend>
            <div className="space-y-2">
              {DIGEST_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  htmlFor={`digest-${opt.value}`}
                  aria-label={opt.label}
                  className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:bg-muted/50"
                >
                  <input
                    id={`digest-${opt.value}`}
                    type="radio"
                    name="digest"
                    value={opt.value}
                    checked={prefs.email_digest === opt.value}
                    onChange={() => update({ email_digest: opt.value })}
                    className="accent-primary"
                  />
                  <span>
                    <span className="block text-sm font-medium text-foreground">{opt.label}</span>
                    <span className="block text-xs text-muted-foreground">{opt.desc}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
        )}
      </Section>

      {/* Severity Threshold */}
      <Section title="Severity Threshold">
        <p className="mb-3 text-xs text-muted-foreground">
          Only receive notifications for incidents at or above this severity level
        </p>
        <div className="space-y-2">
          {SEVERITY_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              htmlFor={`severity-${opt.value}`}
              aria-label={opt.label}
              className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:bg-muted/50"
            >
              <input
                id={`severity-${opt.value}`}
                type="radio"
                name="severity"
                value={opt.value}
                checked={prefs.min_severity === opt.value}
                onChange={() => update({ min_severity: opt.value })}
                className="accent-primary"
              />
              <span>
                <span className="block text-sm font-medium text-foreground">{opt.label}</span>
                <span className="block text-xs text-muted-foreground">{opt.desc}</span>
              </span>
            </label>
          ))}
        </div>
      </Section>

      {/* Category Filters */}
      <Section title="Detection Categories">
        <p className="mb-3 text-xs text-muted-foreground">
          Select which detection categories trigger notifications
        </p>
        <div className="flex flex-wrap gap-2">
          {ALL_CATEGORIES.map((cat) => {
            const active = prefs.categories.includes(cat.value);
            return (
              <button
                key={cat.value}
                type="button"
                onClick={() => toggleCategory(cat.value)}
                className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                  active
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
              >
                {cat.label}
              </button>
            );
          })}
        </div>
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={() => update({ categories: ALL_CATEGORIES.map((c) => c.value) })}
            className="text-xs text-primary hover:underline"
          >
            Select all
          </button>
          <button
            type="button"
            onClick={() => update({ categories: [] })}
            className="text-xs text-muted-foreground hover:underline"
          >
            Clear all
          </button>
        </div>
      </Section>

      {/* In-App & Slack */}
      <Section title="Other Channels">
        <div className="space-y-3">
          <Toggle
            label="In-app notifications"
            desc="Show notifications in the dashboard"
            checked={prefs.in_app_enabled}
            onChange={(v) => update({ in_app_enabled: v })}
          />
          <Toggle
            label="Slack direct messages"
            desc="Receive DMs via connected Slack workspace"
            checked={prefs.slack_dm_enabled}
            onChange={(v) => update({ slack_dm_enabled: v })}
          />
        </div>
      </Section>

      {/* Quiet Hours */}
      <Section title="Quiet Hours">
        <Toggle
          label="Enable quiet hours"
          desc="Suppress non-critical notifications during specified times (UTC)"
          checked={prefs.quiet_hours_enabled}
          onChange={(v) => update({ quiet_hours_enabled: v })}
        />
        {prefs.quiet_hours_enabled && (
          <div className="mt-4 flex items-center gap-3">
            <div>
              <label htmlFor="quiet-hours-start" className="mb-1 block text-xs font-medium text-foreground">
                Start (UTC)
              </label>
              <input
                id="quiet-hours-start"
                type="time"
                value={prefs.quiet_hours_start}
                onChange={(e) => update({ quiet_hours_start: e.target.value })}
                className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
              />
            </div>
            <span className="mt-5 text-sm text-muted-foreground">to</span>
            <div>
              <label htmlFor="quiet-hours-end" className="mb-1 block text-xs font-medium text-foreground">
                End (UTC)
              </label>
              <input
                id="quiet-hours-end"
                type="time"
                value={prefs.quiet_hours_end}
                onChange={(e) => update({ quiet_hours_end: e.target.value })}
                className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
              />
            </div>
          </div>
        )}
      </Section>

      {/* Save */}
      <div className="sticky bottom-0 flex items-center justify-end gap-3 border-t border-border bg-background py-4">
        {dirty && (
          <span className="text-xs text-muted-foreground">Unsaved changes</span>
        )}
        <button
          disabled={!dirty || saveMutation.isPending}
          onClick={() => saveMutation.mutate(prefs)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {saveMutation.isPending ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>

      {saveMutation.isError && (
        <p className="mt-2 text-sm text-red-500">
          Failed to save. Please try again.
        </p>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6 rounded-xl border border-border bg-card p-6">
      <h2 className="mb-4 text-sm font-semibold text-foreground">{title}</h2>
      {children}
    </div>
  );
}

function Toggle({
  label,
  desc,
  checked,
  onChange,
}: {
  label: string;
  desc?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        {desc && <p className="text-xs text-muted-foreground">{desc}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-11 rounded-full transition-colors ${
          checked ? 'bg-primary' : 'bg-muted'
        }`}
      >
        <span
          className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
            checked ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </label>
  );
}
