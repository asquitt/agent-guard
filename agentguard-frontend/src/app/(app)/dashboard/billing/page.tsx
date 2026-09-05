'use client';

import { useMutation, useQuery } from '@tanstack/react-query';

import { createCustomerPortal, getBillingStatus } from '@/lib/api';
import type { BillingStatus } from '@/types';

export default function BillingPage() {
  const {
    data: billing,
    isLoading,
    isError,
    error,
  } = useQuery<BillingStatus>({
    queryKey: ['billing'],
    queryFn: getBillingStatus,
  });

  const portalMutation = useMutation({
    mutationFn: createCustomerPortal,
    onSuccess: (data) => {
      window.location.href = data.portalUrl;
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center" aria-label="Loading billing record">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary/20 border-t-primary-600" />
      </div>
    );
  }

  if (isError || !billing) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-foreground">Access &amp; Usage</h1>
        <div role="alert" className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-700 dark:text-red-300">
          The current access and usage record could not be loaded.
          {error instanceof Error && <span className="mt-1 block">{error.message}</span>}
        </div>
      </div>
    );
  }

  const usageCount = billing.monthlyRequestCount;
  const usageLimit = billing.requestLimit;
  const usagePercent = usageLimit
    ? Math.min((usageCount / usageLimit) * 100, 100)
    : null;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Access &amp; Usage</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Values below come from this organization&apos;s current backend record.
          They are not a public price sheet or service-level commitment.
        </p>
      </div>

      <div className="mb-8 rounded-xl border border-border bg-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Recorded access tier</h2>
            <p className="mt-1 text-2xl font-bold capitalize text-primary">
              {billing.planTier || 'Not configured'}
            </p>
            {billing.subscriptionStatus ? (
              <span className="mt-2 inline-block rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                Subscription record: {billing.subscriptionStatus}
              </span>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">
                No self-service subscription is recorded. Production,
                commercial, support, and availability terms require a separate
                written agreement.
              </p>
            )}
          </div>

          {billing.subscriptionStatus && (
            <button
              type="button"
              onClick={() => portalMutation.mutate()}
              disabled={portalMutation.isPending}
              className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50 disabled:opacity-50"
            >
              {portalMutation.isPending ? 'Opening...' : 'Open Billing Portal'}
            </button>
          )}
        </div>

        <div className="mt-6 border-t border-border pt-6">
          <div className="flex items-center justify-between gap-4 text-sm">
            <span className="text-muted-foreground">Recorded requests this month</span>
            <span className="font-medium text-foreground">
              {usageLimit
                ? `${usageCount.toLocaleString()} / ${usageLimit.toLocaleString()}`
                : usageCount.toLocaleString()}
            </span>
          </div>

          {usagePercent != null ? (
            <>
              <div className="mt-2 h-3 overflow-hidden rounded-full bg-muted">
                <div
                  className={`h-full rounded-full transition-all ${
                    usagePercent >= 90
                      ? 'bg-red-500'
                      : usagePercent >= 70
                        ? 'bg-yellow-500'
                        : 'bg-primary'
                  }`}
                  style={{ width: `${usagePercent}%` }}
                />
              </div>
              {usagePercent >= 90 && (
                <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                  The recorded request allowance is nearly reached. Confirm the
                  written traffic boundary before increasing volume.
                </p>
              )}
            </>
          ) : (
            <p className="mt-2 text-xs text-muted-foreground">
              The billing service did not return a request limit. That absence
              does not mean usage is unlimited.
            </p>
          )}

          {billing.currentPeriodEnd && (
            <p className="mt-4 text-xs text-muted-foreground">
              Recorded billing period ends{' '}
              {new Date(billing.currentPeriodEnd).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>

      {portalMutation.isError && (
        <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-700 dark:text-red-300">
          {portalMutation.error instanceof Error
            ? portalMutation.error.message
            : 'The billing portal is not available for this organization.'}
        </div>
      )}

      <div className="rounded-xl border border-border bg-muted/30 p-5">
        <h2 className="text-sm font-semibold text-foreground">Evaluation boundary</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          This page intentionally does not offer hard-coded upgrades, prices,
          features, request volumes, support promises, or service-level commitments. Those
          details must come from a configured billing catalog and an applicable
          agreement, not frontend constants.
        </p>
      </div>
    </div>
  );
}
