'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { getBillingStatus, createCheckoutSession, createCustomerPortal } from '@/lib/api';
import type { BillingStatus } from '@/types';

const PLANS = [
  {
    name: 'Starter',
    tier: 'starter',
    price: '$99/mo',
    requests: '10,000',
    features: ['5 detectors', 'Email alerts', 'Basic dashboard'],
  },
  {
    name: 'Pro',
    tier: 'pro',
    price: '$499/mo',
    requests: '100,000',
    features: ['All detectors', 'Slack + PagerDuty alerts', 'Advanced analytics', 'Priority support'],
  },
  {
    name: 'Enterprise',
    tier: 'enterprise',
    price: 'Custom',
    requests: 'Unlimited',
    features: ['Everything in Pro', 'SSO/SAML', 'Dedicated support', 'Custom detectors', 'SLA guarantee'],
  },
];

export default function BillingPage() {
  const { data: billing, isLoading } = useQuery<BillingStatus>({
    queryKey: ['billing'],
    queryFn: getBillingStatus,
  });

  const checkoutMutation = useMutation({
    mutationFn: (priceId: string) => createCheckoutSession(priceId),
    onSuccess: (data) => {
      window.location.href = data.checkoutUrl;
    },
  });

  const portalMutation = useMutation({
    mutationFn: () => createCustomerPortal(),
    onSuccess: (data) => {
      window.location.href = data.portalUrl;
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  const currentTier = billing?.planTier ?? 'starter';
  const usageCount = billing?.monthlyRequestCount ?? 0;
  const usageLimit = billing?.requestLimit;
  const usagePercent = usageLimit ? Math.min((usageCount / usageLimit) * 100, 100) : 0;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Billing</h1>
        <p className="text-sm text-gray-500">
          Manage your subscription and monitor usage
        </p>
      </div>

      {/* Current Plan + Usage */}
      <div className="mb-8 rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Current Plan</h2>
            <p className="mt-1 text-2xl font-bold capitalize text-primary-600">
              {currentTier}
            </p>
            {billing?.subscriptionStatus && (
              <span className="mt-1 inline-block rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                {billing.subscriptionStatus}
              </span>
            )}
          </div>
          {billing?.subscriptionStatus && (
            <button
              onClick={() => portalMutation.mutate()}
              disabled={portalMutation.isPending}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {portalMutation.isPending ? 'Loading...' : 'Manage Subscription'}
            </button>
          )}
        </div>

        {/* Usage Bar */}
        {usageLimit && (
          <div className="mt-6">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Monthly API Requests</span>
              <span className="font-medium text-gray-900">
                {usageCount.toLocaleString()} / {usageLimit.toLocaleString()}
              </span>
            </div>
            <div className="mt-2 h-3 overflow-hidden rounded-full bg-gray-200">
              <div
                className={`h-full rounded-full transition-all ${
                  usagePercent >= 90
                    ? 'bg-red-500'
                    : usagePercent >= 70
                      ? 'bg-yellow-500'
                      : 'bg-primary-500'
                }`}
                style={{ width: `${usagePercent}%` }}
              />
            </div>
            {usagePercent >= 90 && (
              <p className="mt-2 text-xs text-red-600">
                You&apos;re approaching your monthly limit. Consider upgrading your plan.
              </p>
            )}
          </div>
        )}

        {!usageLimit && (
          <div className="mt-4">
            <span className="text-sm text-gray-500">
              {usageCount.toLocaleString()} requests this month (unlimited)
            </span>
          </div>
        )}

        {billing?.currentPeriodEnd && (
          <p className="mt-4 text-xs text-gray-400">
            Current period ends{' '}
            {new Date(billing.currentPeriodEnd).toLocaleDateString()}
          </p>
        )}
      </div>

      {/* Plan Comparison */}
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Plans</h2>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {PLANS.map((plan) => {
          const isCurrent = plan.tier === currentTier;

          return (
            <div
              key={plan.tier}
              className={`rounded-xl border p-6 ${
                isCurrent
                  ? 'border-primary-300 bg-primary-50'
                  : 'border-gray-200 bg-white'
              }`}
            >
              <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
              <p className="mt-1 text-2xl font-bold text-gray-900">{plan.price}</p>
              <p className="mt-1 text-sm text-gray-500">
                {plan.requests} requests/month
              </p>

              <ul className="mt-4 space-y-2">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center text-sm text-gray-600">
                    <span className="mr-2 text-green-500">&#10003;</span>
                    {feature}
                  </li>
                ))}
              </ul>

              <div className="mt-6">
                {isCurrent ? (
                  <span className="block rounded-lg bg-primary-100 px-4 py-2 text-center text-sm font-medium text-primary-700">
                    Current Plan
                  </span>
                ) : plan.tier === 'enterprise' ? (
                  <span className="block rounded-lg bg-gray-100 px-4 py-2 text-center text-sm font-medium text-gray-600">
                    Contact Sales
                  </span>
                ) : (
                  <button
                    onClick={() => checkoutMutation.mutate(plan.tier)}
                    disabled={checkoutMutation.isPending}
                    className="block w-full rounded-lg bg-primary-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                  >
                    {checkoutMutation.isPending ? 'Loading...' : 'Upgrade'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Error display */}
      {(checkoutMutation.isError || portalMutation.isError) && (
        <div className="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">
          {checkoutMutation.error?.message || portalMutation.error?.message || 'Billing service is not available'}
        </div>
      )}
    </div>
  );
}
