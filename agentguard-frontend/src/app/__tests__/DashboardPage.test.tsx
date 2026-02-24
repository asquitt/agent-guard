import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockRefetch = vi.fn();

let metricsLoading = false;
let metricsError = false;
let metricsData: Record<string, unknown> | undefined;
let riskData: Record<string, unknown> | undefined;

vi.mock('@tanstack/react-query', () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => {
    if (queryKey[0] === 'dashboard') {
      return {
        data: metricsData,
        isLoading: metricsLoading,
        isError: metricsError,
        refetch: mockRefetch,
      };
    }
    if (queryKey[0] === 'risk-score') {
      return { data: riskData };
    }
    return { data: undefined, isLoading: false, isError: false };
  },
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { name: 'Alice', email: 'alice@test.com' },
    isAuthenticated: true,
  }),
}));

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ status: 'disconnected', lastEvent: null }),
}));

vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({ toast: vi.fn(), success: vi.fn(), error: vi.fn() }),
}));

vi.mock('@/lib/format', () => ({
  timeAgo: () => '2h ago',
}));

vi.mock('@/lib/constants', () => ({
  SEVERITY_COLORS: {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
  },
  STATUS_COLORS: {
    open: 'bg-blue-100 text-blue-700',
    resolved: 'bg-green-100 text-green-700',
  },
  TREND_COLORS: {
    improving: '#22c55e',
    stable: '#a1a1aa',
    degrading: '#ef4444',
  },
}));

vi.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock('@/components/charts/Sparkline', () => ({
  Sparkline: () => <div data-testid="sparkline" />,
}));

vi.mock('@/components/dashboard/ActivityFeed', () => ({
  ActivityFeed: () => <div data-testid="activity-feed">Activity Feed</div>,
}));

vi.mock('@/components/dashboard/CostAnalytics', () => ({
  CostAnalyticsSection: () => <div data-testid="cost-analytics">Cost</div>,
}));

vi.mock('@/components/dashboard/DetectionEfficacy', () => ({
  DetectionEfficacySection: () => <div data-testid="detection-efficacy">Efficacy</div>,
}));

vi.mock('@/components/dashboard/SlaMetrics', () => ({
  SlaMetricsSection: () => <div data-testid="sla-metrics">SLA</div>,
}));

vi.mock('@/components/ui/Skeleton', () => ({
  DashboardSkeleton: () => <div data-testid="dashboard-skeleton">Loading...</div>,
}));

vi.mock('@/components/ui/QueryError', () => ({
  QueryError: ({ message, onRetry }: { message: string; onRetry: () => void }) => (
    <div data-testid="query-error">
      <p>{message}</p>
      <button onClick={onRetry}>Retry</button>
    </div>
  ),
}));

import DashboardPage from '@/app/(app)/dashboard/page';

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    metricsLoading = false;
    metricsError = false;
    metricsData = undefined;
    riskData = undefined;
  });

  it('renders welcome message with user name', () => {
    metricsData = {
      totalIncidents: 5,
      openIncidents: 2,
      incidentsBySeverity: [],
      incidentsByStatus: [],
      recentIncidents: [],
    };
    render(<DashboardPage />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Welcome back, Alice')).toBeInTheDocument();
  });

  it('renders loading skeleton when data is loading', () => {
    metricsLoading = true;
    render(<DashboardPage />);
    expect(screen.getByTestId('dashboard-skeleton')).toBeInTheDocument();
  });

  it('renders error state with retry button', async () => {
    metricsError = true;
    const { getByTestId } = render(<DashboardPage />);
    expect(getByTestId('query-error')).toBeInTheDocument();
    expect(screen.getByText('Failed to load dashboard metrics.')).toBeInTheDocument();
  });

  it('renders metric cards with data', () => {
    metricsData = {
      totalIncidents: 42,
      openIncidents: 7,
      incidentsBySeverity: [{ severity: 'critical', count: 3 }],
      incidentsByStatus: [{ status: 'open', count: 7 }],
      recentIncidents: [],
    };
    render(<DashboardPage />);
    expect(screen.getByText('Total Incidents')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Open Incidents')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('renders severity breakdown badges', () => {
    metricsData = {
      totalIncidents: 10,
      openIncidents: 3,
      incidentsBySeverity: [
        { severity: 'critical', count: 3 },
        { severity: 'high', count: 7 },
      ],
      incidentsByStatus: [],
      recentIncidents: [],
    };
    render(<DashboardPage />);
    expect(screen.getByText('By Severity')).toBeInTheDocument();
    expect(screen.getByText(/critical/)).toBeInTheDocument();
  });

  it('renders recent incidents table when incidents exist', () => {
    metricsData = {
      totalIncidents: 1,
      openIncidents: 1,
      incidentsBySeverity: [],
      incidentsByStatus: [],
      recentIncidents: [
        {
          id: 'inc-1',
          title: 'PII Found',
          severity: 'critical',
          status: 'open',
          category: 'pii_leak',
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
    };
    render(<DashboardPage />);
    expect(screen.getByText('Recent Incidents')).toBeInTheDocument();
    expect(screen.getByText('PII Found')).toBeInTheDocument();
    expect(screen.getByText('View all')).toBeInTheDocument();
  });

  it('renders empty state when no recent incidents', () => {
    metricsData = {
      totalIncidents: 0,
      openIncidents: 0,
      incidentsBySeverity: [],
      incidentsByStatus: [],
      recentIncidents: [],
    };
    render(<DashboardPage />);
    expect(screen.getByText('No incidents yet')).toBeInTheDocument();
  });

  it('renders risk widget when risk data has incidents', () => {
    metricsData = {
      totalIncidents: 5,
      openIncidents: 2,
      incidentsBySeverity: [],
      incidentsByStatus: [],
      recentIncidents: [],
    };
    riskData = {
      grade: 'B',
      overallScore: 35,
      trendDirection: 'improving',
      criticalOpen: 1,
      totalIncidents: 5,
      trend: [{ score: 40 }, { score: 35 }],
    };
    render(<DashboardPage />);
    expect(screen.getByText('B')).toBeInTheDocument();
    expect(screen.getByText(/Risk Score: 35\/100/)).toBeInTheDocument();
    expect(screen.getByText('View details →')).toBeInTheDocument();
  });

  it('renders sub-sections (SLA, Cost, Efficacy, Activity)', () => {
    metricsData = {
      totalIncidents: 0,
      openIncidents: 0,
      incidentsBySeverity: [],
      incidentsByStatus: [],
      recentIncidents: [],
    };
    render(<DashboardPage />);
    expect(screen.getByTestId('sla-metrics')).toBeInTheDocument();
    expect(screen.getByTestId('cost-analytics')).toBeInTheDocument();
    expect(screen.getByTestId('detection-efficacy')).toBeInTheDocument();
    expect(screen.getByTestId('activity-feed')).toBeInTheDocument();
  });
});
