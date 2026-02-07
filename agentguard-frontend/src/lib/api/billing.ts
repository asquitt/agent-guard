/**
 * Billing API client functions.
 */

import type { BillingStatus, CheckoutSessionResponse, CustomerPortalResponse } from '@/types';
import { apiFetch } from './client';

export async function getBillingStatus(): Promise<BillingStatus> {
  return apiFetch<BillingStatus>('/billing/status');
}

export async function createCheckoutSession(
  priceId: string,
): Promise<CheckoutSessionResponse> {
  return apiFetch<CheckoutSessionResponse>('/billing/checkout', {
    method: 'POST',
    body: JSON.stringify({ priceId }),
  });
}

export async function createCustomerPortal(): Promise<CustomerPortalResponse> {
  return apiFetch<CustomerPortalResponse>('/billing/portal', {
    method: 'POST',
  });
}
