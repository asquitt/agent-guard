import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

let destLoading = false;
let destError = false;
let destData: Record<string, unknown> | undefined;
const mockRefetch = vi.fn();
const mockMutate = vi.fn();

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    data: destData,
    isLoading: destLoading,
    isError: destError,
    refetch: mockRefetch,
  }),
  useMutation: () => ({
    mutate: mockMutate,
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useQueryClient: () => ({
    invalidateQueries: vi.fn(),
  }),
}));

vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({ toast: vi.fn(), success: vi.fn(), error: vi.fn() }),
}));

vi.mock('@/components/ui/Skeleton', () => ({
  Skeleton: () => <div data-testid="skeleton">Loading...</div>,
}));

vi.mock('@/components/ui/EmptyState', () => ({
  EmptyState: ({ title }: { title: string }) => <div data-testid="empty-state">{title}</div>,
}));

vi.mock('@/components/ui/QueryError', () => ({
  QueryError: ({ message, onRetry }: { message: string; onRetry: () => void }) => (
    <div data-testid="query-error">
      <p>{message}</p>
      <button onClick={onRetry}>Retry</button>
    </div>
  ),
}));

vi.mock('@/components/ui/ConfirmDialog', () => ({
  ConfirmDialog: () => null,
}));

vi.mock('@/lib/api', () => ({
  listDestinations: vi.fn(),
  createDestination: vi.fn(),
  updateDestination: vi.fn(),
  deleteDestination: vi.fn(),
  testDestination: vi.fn(),
}));

vi.mock('lucide-react', () => ({
  Bell: () => <span>Bell</span>,
}));

import AlertsPage from '@/app/(app)/dashboard/alerts/page';

describe('AlertsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    destLoading = false;
    destError = false;
    destData = undefined;
  });

  it('renders page title', () => {
    destData = { items: [] };
    render(<AlertsPage />);
    expect(screen.getByText('Alert Destinations')).toBeInTheDocument();
  });

  it('renders add destination button', () => {
    destData = { items: [] };
    render(<AlertsPage />);
    expect(screen.getByText('Add destination')).toBeInTheDocument();
  });

  it('renders error state', () => {
    destError = true;
    render(<AlertsPage />);
    expect(screen.getByTestId('query-error')).toBeInTheDocument();
  });

  it('renders empty state when no destinations', () => {
    destData = { items: [] };
    render(<AlertsPage />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('renders destination cards when data exists', () => {
    destData = {
      items: [
        { id: 'd-1', name: 'Slack Channel', destinationType: 'slack', isActive: true, config: {}, createdAt: '2024-01-01T00:00:00Z', updatedAt: '2024-01-01T00:00:00Z' },
      ],
    };
    render(<AlertsPage />);
    expect(screen.getByText('Slack Channel')).toBeInTheDocument();
  });
});
