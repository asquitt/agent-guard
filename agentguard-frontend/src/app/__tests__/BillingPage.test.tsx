import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockUseMutation, mockUseQuery } = vi.hoisted(() => ({
  mockUseMutation: vi.fn(),
  mockUseQuery: vi.fn(),
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: mockUseMutation,
  useQuery: mockUseQuery,
}));

vi.mock('@/lib/api', () => ({
  createCustomerPortal: vi.fn(),
  getBillingStatus: vi.fn(),
}));

import BillingPage from '@/app/(app)/dashboard/billing/page';

describe('billing release truth', () => {
  beforeEach(() => {
    mockUseMutation.mockReset();
    mockUseQuery.mockReset();
    mockUseMutation.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
    });
  });

  it('renders only the organization billing record, without hard-coded offers', () => {
    mockUseQuery.mockReturnValue({
      data: {
        planTier: 'pro',
        subscriptionStatus: 'active',
        currentPeriodEnd: '2026-09-30T00:00:00Z',
        monthlyRequestCount: 42,
        requestLimit: 100,
      },
      isLoading: false,
      isError: false,
      error: null,
    });

    const { container } = render(<BillingPage />);
    const copy = container.textContent ?? '';

    expect(screen.getByText('pro')).toBeInTheDocument();
    expect(screen.getByText('42 / 100')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open Billing Portal' })).toBeInTheDocument();
    expect(copy).not.toContain('$99');
    expect(copy).not.toContain('$499');
    expect(copy).not.toContain('Unlimited');
    expect(copy).not.toContain('Upgrade');
    expect(copy).not.toContain('SLA guarantee');
  });

  it('does not infer an unlimited plan from an absent limit', () => {
    mockUseQuery.mockReturnValue({
      data: {
        planTier: 'starter',
        subscriptionStatus: null,
        currentPeriodEnd: null,
        monthlyRequestCount: 7,
        requestLimit: null,
      },
      isLoading: false,
      isError: false,
      error: null,
    });

    render(<BillingPage />);

    expect(screen.getByText(/does not mean usage is unlimited/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Open Billing Portal' })).not.toBeInTheDocument();
  });

  it('shows an unknown state when the billing record cannot load', () => {
    mockUseQuery.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Billing unavailable'),
    });

    render(<BillingPage />);

    expect(screen.getByRole('alert')).toHaveTextContent(
      'The current access and usage record could not be loaded',
    );
  });
});
