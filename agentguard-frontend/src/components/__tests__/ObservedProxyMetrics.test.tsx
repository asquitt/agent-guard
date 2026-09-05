import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockUseQuery } = vi.hoisted(() => ({ mockUseQuery: vi.fn() }));

vi.mock('@tanstack/react-query', () => ({ useQuery: mockUseQuery }));

vi.mock('@/lib/api', () => ({ getSlaMetrics: vi.fn() }));

import { SlaMetricsSection } from '@/components/dashboard/SlaMetrics';

describe('observed proxy metrics', () => {
  beforeEach(() => mockUseQuery.mockReset());

  it('does not present an empty period as perfect availability', () => {
    mockUseQuery.mockReturnValue({
      isLoading: false,
      data: {
        p50LatencyMs: null,
        p95LatencyMs: null,
        p99LatencyMs: null,
        errorRate: 0,
        totalRequests: 0,
        avgThroughputPerHour: 0,
        uptimePct: 100,
        byProvider: [],
      },
    });

    render(<SlaMetricsSection />);

    expect(screen.getByText('Observed Proxy Metrics')).toBeInTheDocument();
    expect(screen.getByText(/not a service-level commitment/i)).toBeInTheDocument();
    expect(screen.getAllByText('No recorded requests in this period')).toHaveLength(2);
    expect(screen.queryByText('100.00%')).not.toBeInTheDocument();
    expect(screen.queryByText('0.00%')).not.toBeInTheDocument();
    expect(screen.queryByText('0/hr')).not.toBeInTheDocument();
  });

  it('renders unknown metrics when the request fails', () => {
    mockUseQuery.mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
    });

    render(<SlaMetricsSection />);

    expect(screen.getByRole('alert')).toHaveTextContent('Observed metrics are unavailable');
    expect(screen.getAllByText('—')).toHaveLength(4);
    expect(screen.queryByText('0.00%')).not.toBeInTheDocument();
    expect(screen.queryByText('0/hr')).not.toBeInTheDocument();
  });

  it('labels the backend ratio as an observed request metric', () => {
    mockUseQuery.mockReturnValue({
      isLoading: false,
      data: {
        p50LatencyMs: 25,
        p95LatencyMs: 50,
        p99LatencyMs: 80,
        errorRate: 0.1,
        totalRequests: 10,
        avgThroughputPerHour: 2,
        uptimePct: 90,
        byProvider: [],
      },
    });

    render(<SlaMetricsSection />);

    expect(screen.getByText('Successful response ratio')).toBeInTheDocument();
    expect(screen.getByText('90.00%')).toBeInTheDocument();
    expect(screen.getByText('Based on 10 recorded requests')).toBeInTheDocument();
    expect(screen.queryByText(/uptime/i)).not.toBeInTheDocument();
  });
});
