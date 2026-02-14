'use client';

import { clsx } from 'clsx';
import { Shield, AlertTriangle, CheckCircle, XCircle, Eye, Clock } from 'lucide-react';
import type { IncidentDetail } from '@/types';
import { SEVERITY_COLORS } from '@/lib/constants';
import { formatDateTime } from '@/lib/format';

interface TimelineEvent {
  id: string;
  label: string;
  description: string;
  time: string;
  icon: typeof Shield;
  color: string;
  dotColor: string;
}

function buildTimeline(incident: IncidentDetail): TimelineEvent[] {
  const events: TimelineEvent[] = [];

  // 1. Detection event
  events.push({
    id: 'detected',
    label: 'Incident Detected',
    description: `${incident.category.replace(/_/g, ' ')} detected by ${incident.detectorId ? `detector ${incident.detectorId.slice(0, 8)}` : 'pipeline'}`,
    time: incident.createdAt,
    icon: AlertTriangle,
    color: 'text-red-400',
    dotColor: 'bg-red-500',
  });

  // 2. Action taken (if any)
  if (incident.actionTaken && incident.actionTaken !== 'None') {
    events.push({
      id: 'action',
      label: `Action: ${incident.actionTaken}`,
      description: getActionDescription(incident.actionTaken),
      time: incident.createdAt,
      icon: Shield,
      color: 'text-orange-400',
      dotColor: 'bg-orange-500',
    });
  }

  // 3. User actions from the timeline
  for (const action of incident.actions) {
    events.push({
      id: action.id,
      label: action.actionType.replace(/_/g, ' '),
      description: getActionNote(action.details),
      time: action.createdAt,
      icon: getActionIcon(action.actionType),
      color: getActionColor(action.actionType),
      dotColor: getActionDotColor(action.actionType),
    });
  }

  // 4. Resolution event
  if (incident.resolvedAt) {
    events.push({
      id: 'resolved',
      label: incident.status === 'dismissed' ? 'Dismissed' : 'Resolved',
      description: `Incident ${incident.status}`,
      time: incident.resolvedAt,
      icon: incident.status === 'dismissed' ? XCircle : CheckCircle,
      color: incident.status === 'dismissed' ? 'text-zinc-400' : 'text-green-400',
      dotColor: incident.status === 'dismissed' ? 'bg-zinc-500' : 'bg-green-500',
    });
  }

  return events;
}

function getActionDescription(action: string): string {
  switch (action.toUpperCase()) {
    case 'BLOCK': return 'Request was blocked by the detection pipeline';
    case 'REDACT': return 'Sensitive content was redacted from the response';
    case 'WARN': return 'Warning logged; request was allowed through';
    case 'MONITOR': return 'Detection recorded for monitoring purposes';
    default: return `Action "${action}" was taken automatically`;
  }
}

function getActionNote(details: Record<string, unknown>): string {
  if (details && typeof details.note === 'string') return details.note;
  return '';
}

function getActionIcon(actionType: string): typeof Shield {
  switch (actionType) {
    case 'investigate': return Eye;
    case 'escalate': return AlertTriangle;
    default: return Clock;
  }
}

function getActionColor(actionType: string): string {
  switch (actionType) {
    case 'investigate': return 'text-blue-400';
    case 'escalate': return 'text-orange-400';
    default: return 'text-muted-foreground';
  }
}

function getActionDotColor(actionType: string): string {
  switch (actionType) {
    case 'investigate': return 'bg-blue-500';
    case 'escalate': return 'bg-orange-500';
    default: return 'bg-zinc-500';
  }
}

export function DetectionTimeline({ incident }: { incident: IncidentDetail }) {
  const events = buildTimeline(incident);
  const durationMs = incident.resolvedAt
    ? new Date(incident.resolvedAt).getTime() - new Date(incident.createdAt).getTime()
    : null;

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <h2 className="text-lg font-semibold text-foreground">Detection Timeline</h2>
        <div className="flex items-center gap-3">
          <span
            className={clsx(
              'rounded-full px-2.5 py-0.5 text-xs font-medium',
              SEVERITY_COLORS[incident.severity] ?? 'bg-muted text-muted-foreground',
            )}
          >
            {incident.severity}
          </span>
          {durationMs != null && (
            <span className="text-xs text-muted-foreground">
              {formatDuration(durationMs)} to resolve
            </span>
          )}
        </div>
      </div>

      <div className="px-6 py-4">
        <div className="relative">
          {events.map((event, i) => {
            const Icon = event.icon;
            const isLast = i === events.length - 1;
            return (
              <div key={event.id} className="relative flex gap-4 pb-6 last:pb-0">
                {/* Vertical line */}
                {!isLast && (
                  <div className="absolute left-[15px] top-8 h-[calc(100%-1.5rem)] w-px bg-border" />
                )}

                {/* Dot / icon */}
                <div className={clsx('relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full', event.dotColor + '/20')}>
                  <Icon className={clsx('h-4 w-4', event.color)} />
                </div>

                {/* Content */}
                <div className="flex-1 pt-0.5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-foreground">{event.label}</p>
                    <time className="text-xs text-muted-foreground" dateTime={event.time}>
                      {formatDateTime(event.time)}
                    </time>
                  </div>
                  {event.description && (
                    <p className="mt-0.5 text-xs text-muted-foreground">{event.description}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}
