'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { listReviews, getReviewStats, decideReview, escalateReview } from '@/lib/api';
import type { ReviewItem } from '@/lib/api';
import { SEVERITY_COLORS, REVIEW_STATUS_COLORS } from '@/lib/constants';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

const REVIEW_STATUSES = ['pending', 'approved', 'rejected', 'escalated', 'expired'] as const;

export default function ReviewsPage() {
  const queryClient = useQueryClient();
  const [filterStatus, setFilterStatus] = useState('pending');
  const [filterSeverity, setFilterSeverity] = useState('');

  const { data: stats } = useQuery({
    queryKey: ['review-stats'],
    queryFn: () => getReviewStats(30),
  });

  const { data, isLoading } = useQuery({
    queryKey: ['reviews', filterStatus, filterSeverity],
    queryFn: () =>
      listReviews({
        status: filterStatus || undefined,
        severity: filterSeverity || undefined,
        limit: 100,
      }),
  });

  const items = data?.items ?? [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Review Queue</h1>
        <p className="text-sm text-muted-foreground">
          Human-in-the-loop oversight for AI agent decisions
        </p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <StatCard label="Pending" value={stats.pending} highlight={stats.pending > 0} />
          <StatCard label="Approved" value={stats.approved} color="text-green-600" />
          <StatCard label="Rejected" value={stats.rejected} color="text-red-600" />
          <StatCard label="Escalated" value={stats.escalated} color="text-orange-600" />
          <StatCard label="Expired" value={stats.expired} />
          <StatCard
            label="Avg Review Time"
            value={stats.avgReviewTimeMinutes != null ? `${stats.avgReviewTimeMinutes.toFixed(0)}m` : '-'}
          />
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          {REVIEW_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Items list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-border bg-card py-16 text-center">
          <p className="text-sm text-muted-foreground">No items in the review queue</p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            Items appear here when detections require human approval
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <ReviewCard
              key={item.id}
              item={item}
              onRefresh={() => {
                queryClient.invalidateQueries({ queryKey: ['reviews'] });
                queryClient.invalidateQueries({ queryKey: ['review-stats'] });
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  highlight,
  color,
}: {
  label: string;
  value: number | string;
  highlight?: boolean;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className={clsx('text-2xl font-bold', highlight ? 'text-yellow-600' : color ?? 'text-foreground')}>
        {value}
      </p>
    </div>
  );
}

function ReviewCard({
  item,
  onRefresh,
}: {
  item: ReviewItem;
  onRefresh: () => void;
}) {
  const [reason, setReason] = useState('');
  const [showActions, setShowActions] = useState(false);
  const [confirmReject, setConfirmReject] = useState(false);

  const approveMutation = useMutation({
    mutationFn: () => decideReview(item.id, 'approved', reason || undefined),
    onSuccess: onRefresh,
  });

  const rejectMutation = useMutation({
    mutationFn: () => decideReview(item.id, 'rejected', reason || undefined),
    onSuccess: onRefresh,
  });

  const escalateMutation = useMutation({
    mutationFn: () => escalateReview(item.id),
    onSuccess: onRefresh,
  });

  const isPending = item.status === 'pending' || item.status === 'escalated';
  const isOverdue =
    item.escalationDeadline && new Date(item.escalationDeadline) < new Date();

  return (
    <div
      className={clsx(
        'rounded-xl border bg-card p-5',
        isOverdue ? 'border-red-500/40' : 'border-border',
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground">{item.title}</h3>
            <span
              className={clsx(
                'rounded-full px-2 py-0.5 text-xs font-medium',
                SEVERITY_COLORS[item.severity] ?? 'bg-muted text-muted-foreground',
              )}
            >
              {item.severity}
            </span>
            <span
              className={clsx(
                'rounded-full px-2 py-0.5 text-xs font-medium',
                REVIEW_STATUS_COLORS[item.status] ?? 'bg-muted text-muted-foreground',
              )}
            >
              {item.status}
            </span>
            {item.escalationLevel > 0 && (
              <span className="rounded-full bg-orange-500/10 px-2 py-0.5 text-xs font-medium text-orange-400">
                L{item.escalationLevel}
              </span>
            )}
          </div>
          {item.description && (
            <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
          )}
          <div className="mt-2 flex gap-4 text-xs text-muted-foreground/60">
            {item.category && <span>Category: {item.category}</span>}
            <span>Created: {new Date(item.createdAt).toLocaleString()}</span>
            {item.escalationDeadline && (
              <span className={isOverdue ? 'text-red-500 font-medium' : ''}>
                Deadline: {new Date(item.escalationDeadline).toLocaleString()}
              </span>
            )}
            {item.reviewedAt && (
              <span>Reviewed: {new Date(item.reviewedAt).toLocaleString()}</span>
            )}
          </div>
          {item.decisionReason && (
            <p className="mt-2 rounded bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
              Reason: {item.decisionReason}
            </p>
          )}
        </div>

        {isPending && (
          <button
            onClick={() => setShowActions(!showActions)}
            className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary/100"
          >
            Review
          </button>
        )}
      </div>

      <ConfirmDialog
        open={confirmReject}
        title="Reject Review"
        description="Reject this review item? This action cannot be undone."
        confirmLabel="Reject"
        variant="danger"
        loading={rejectMutation.isPending}
        onConfirm={() => {
          rejectMutation.mutate();
          setConfirmReject(false);
        }}
        onCancel={() => setConfirmReject(false)}
      />

      {showActions && isPending && (
        <div className="mt-4 border-t border-border pt-4">
          <div className="mb-3">
            <label className="mb-1 block text-xs text-muted-foreground">Decision Reason (optional)</label>
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              placeholder="Provide a reason for your decision..."
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending}
              className="rounded-lg bg-green-600 px-4 py-2 text-xs font-medium text-white hover:bg-green-500 disabled:opacity-50"
            >
              {approveMutation.isPending ? 'Approving...' : 'Approve'}
            </button>
            <button
              onClick={() => setConfirmReject(true)}
              disabled={rejectMutation.isPending}
              className="rounded-lg bg-red-600 px-4 py-2 text-xs font-medium text-white hover:bg-red-500 disabled:opacity-50"
            >
              {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
            </button>
            <button
              onClick={() => escalateMutation.mutate()}
              disabled={escalateMutation.isPending}
              className="rounded-lg border border-orange-500/30 px-4 py-2 text-xs font-medium text-orange-500 hover:bg-orange-500/10 disabled:opacity-50"
            >
              Escalate
            </button>
            <button
              onClick={() => setShowActions(false)}
              className="rounded-lg border border-border px-4 py-2 text-xs font-medium text-muted-foreground hover:bg-muted/50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
