'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import {
  listConversations,
  getConversation,
  getConversationStats,
  updateConversationStatus,
} from '@/lib/api';
import type { Conversation, ConversationDetail } from '@/lib/api';

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-blue-100 text-blue-700',
  completed: 'bg-muted text-muted-foreground',
  escalated: 'bg-red-100 text-red-700',
  flagged: 'bg-yellow-100 text-yellow-700',
};

function RiskBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color =
    pct >= 80 ? 'bg-red-500' : pct >= 60 ? 'bg-orange-500' : pct >= 30 ? 'bg-yellow-500' : 'bg-green-500';
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 rounded-full bg-muted">
        <div className={clsx('h-2 rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground">{pct.toFixed(1)}</span>
    </div>
  );
}

function ConversationReplay({ detail }: { detail: ConversationDetail }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">
          Conversation Replay — {detail.turns.length} turns
        </h3>
        <RiskBar score={detail.riskScore} />
      </div>
      <div className="max-h-96 space-y-2 overflow-y-auto">
        {detail.turns.map((turn) => (
          <div
            key={turn.id}
            className={clsx(
              'rounded-lg border p-3',
              turn.role === 'user'
                ? 'border-blue-200 bg-blue-50'
                : turn.role === 'assistant'
                  ? 'border-border bg-card'
                  : 'border-purple-200 bg-purple-50',
            )}
          >
            <div className="mb-1 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium uppercase text-muted-foreground">
                  #{turn.turnNumber} {turn.role}
                </span>
                {turn.detections.length > 0 && (
                  <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-700">
                    {turn.detections.length} detection{turn.detections.length > 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {turn.riskDelta !== 0 && (
                  <span
                    className={clsx(
                      'text-xs font-medium',
                      turn.riskDelta > 0 ? 'text-red-600' : 'text-green-600',
                    )}
                  >
                    {turn.riskDelta > 0 ? '+' : ''}{turn.riskDelta.toFixed(1)}
                  </span>
                )}
                <span className="text-xs text-muted-foreground/60">
                  cumulative: {turn.cumulativeRisk.toFixed(1)}
                </span>
              </div>
            </div>
            {turn.contentPreview && (
              <p className="text-xs text-foreground">{turn.contentPreview}</p>
            )}
            {turn.detections.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {turn.detections.map((d, i) => (
                  <span
                    key={i}
                    className="rounded bg-red-50 px-1.5 py-0.5 text-xs text-red-600"
                  >
                    {d.category}: {d.title}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ConversationsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['conversation-stats'],
    queryFn: () => getConversationStats(30),
  });

  const { data: conversations, isLoading } = useQuery({
    queryKey: ['conversations', statusFilter, riskFilter],
    queryFn: () =>
      listConversations({
        status: statusFilter || undefined,
        riskLevel: riskFilter || undefined,
        limit: 100,
      }),
  });

  const { data: detail } = useQuery({
    queryKey: ['conversation-detail', selectedId],
    queryFn: () => getConversation(selectedId!),
    enabled: !!selectedId,
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateConversationStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      queryClient.invalidateQueries({ queryKey: ['conversation-stats'] });
      if (selectedId) {
        queryClient.invalidateQueries({ queryKey: ['conversation-detail', selectedId] });
      }
    },
  });

  const items = conversations?.items ?? [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Conversation Analysis</h1>
        <p className="text-sm text-muted-foreground">
          Track multi-turn sessions, detect escalation patterns, and monitor conversation risk
        </p>
      </div>

      {/* Stats */}
      {!statsLoading && stats && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-2xl font-bold text-foreground">{stats.totalConversations}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Active</p>
            <p className="text-2xl font-bold text-blue-600">{stats.activeCount}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Escalated</p>
            <p className="text-2xl font-bold text-red-600">{stats.escalatedCount}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Avg Risk</p>
            <p className="text-2xl font-bold text-foreground">{stats.avgRiskScore}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Avg Turns</p>
            <p className="text-2xl font-bold text-foreground">{stats.avgTurns}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="escalated">Escalated</option>
          <option value="flagged">Flagged</option>
        </select>
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">All Risk Levels</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Conversation list */}
        <div className="space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-border bg-card p-8 text-center">
              <p className="text-sm text-muted-foreground">No conversations found</p>
            </div>
          ) : (
            items.map((conv: Conversation) => (
              <button
                key={conv.id}
                onClick={() => setSelectedId(conv.id)}
                className={clsx(
                  'w-full rounded-xl border bg-card p-4 text-left transition-colors',
                  selectedId === conv.id
                    ? 'border-primary/30 ring-1 ring-primary/20'
                    : 'border-border hover:border-border',
                )}
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground/60">
                    {conv.sessionId.slice(0, 16)}...
                  </span>
                  <div className="flex gap-1.5">
                    <span className={clsx('rounded px-1.5 py-0.5 text-xs', STATUS_COLORS[conv.status])}>
                      {conv.status}
                    </span>
                    <span className={clsx('rounded px-1.5 py-0.5 text-xs', RISK_COLORS[conv.riskLevel])}>
                      {conv.riskLevel}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <RiskBar score={conv.riskScore} />
                  <span className="text-xs text-muted-foreground">{conv.turnCount} turns</span>
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground/60">
                  <span>{new Date(conv.createdAt).toLocaleString()}</span>
                  <span>{conv.totalTokens.toLocaleString()} tokens</span>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Detail panel */}
        <div>
          {selectedId && detail ? (
            <div className="sticky top-4 space-y-4 rounded-xl border border-border bg-card p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-foreground">Session Detail</h2>
                <div className="flex gap-2">
                  {detail.status === 'active' && (
                    <>
                      <button
                        onClick={() => statusMutation.mutate({ id: detail.id, status: 'flagged' })}
                        className="rounded bg-yellow-100 px-2 py-1 text-xs text-yellow-700 hover:bg-yellow-200"
                      >
                        Flag
                      </button>
                      <button
                        onClick={() => statusMutation.mutate({ id: detail.id, status: 'escalated' })}
                        className="rounded bg-red-100 px-2 py-1 text-xs text-red-700 hover:bg-red-200"
                      >
                        Escalate
                      </button>
                      <button
                        onClick={() => statusMutation.mutate({ id: detail.id, status: 'completed' })}
                        className="rounded bg-muted px-2 py-1 text-xs text-foreground hover:bg-muted"
                      >
                        Complete
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Summary */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <p className="text-xs text-muted-foreground">Risk Score</p>
                  <p className="text-lg font-bold text-foreground">{detail.riskScore.toFixed(1)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Turns</p>
                  <p className="text-lg font-bold text-foreground">{detail.turnCount}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Tokens</p>
                  <p className="text-lg font-bold text-foreground">
                    {detail.totalTokens.toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Replay */}
              <ConversationReplay detail={detail} />
            </div>
          ) : (
            <div className="flex items-center justify-center rounded-xl border border-border bg-card py-24">
              <p className="text-sm text-muted-foreground/60">Select a conversation to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
