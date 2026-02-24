import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

let detectorsLoading = false;
let detectorsError = false;
let detectorsData: Record<string, unknown> | undefined;
const mockRefetch = vi.fn();

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    data: detectorsData,
    isLoading: detectorsLoading,
    isError: detectorsError,
    refetch: mockRefetch,
  }),
  useMutation: () => ({
    mutate: vi.fn(),
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

vi.mock('@/lib/api', () => ({
  listDetectors: vi.fn(),
  updateDetector: vi.fn(),
}));

vi.mock('@/lib/constants', () => ({
  MODE_COLORS: {
    MONITOR: 'bg-blue-100 text-blue-700',
    WARN: 'bg-yellow-100 text-yellow-700',
    REDACT: 'bg-orange-100 text-orange-700',
    BLOCK: 'bg-red-100 text-red-700',
  },
}));

vi.mock('lucide-react', () => ({
  Radar: () => <span>Radar</span>,
  X: () => <span>X</span>,
}));

import DetectorsPage from '@/app/(app)/dashboard/detectors/page';

describe('DetectorsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    detectorsLoading = false;
    detectorsError = false;
    detectorsData = undefined;
  });

  it('renders page title', () => {
    detectorsData = { items: [] };
    render(<DetectorsPage />);
    expect(screen.getByText('Detectors')).toBeInTheDocument();
  });

  it('renders error state', () => {
    detectorsError = true;
    render(<DetectorsPage />);
    expect(screen.getByTestId('query-error')).toBeInTheDocument();
  });

  it('renders empty state when no detectors', () => {
    detectorsData = { items: [] };
    render(<DetectorsPage />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('renders detector cards when data exists', () => {
    detectorsData = {
      items: [
        {
          id: 'det-1',
          name: 'PII Detector',
          category: 'pii_leak',
          isActive: true,
          actionMode: 'BLOCK',
          config: {},
          rules: [],
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
      ],
    };
    render(<DetectorsPage />);
    expect(screen.getByText('PII Detector')).toBeInTheDocument();
  });
});
