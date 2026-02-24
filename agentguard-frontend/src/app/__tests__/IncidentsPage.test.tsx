import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

let incidentsLoading = false;
let incidentsError = false;
let incidentsData: Record<string, unknown> | undefined;
const mockRefetch = vi.fn();
const mockMutate = vi.fn();
const mockInvalidate = vi.fn();

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    data: incidentsData,
    isLoading: incidentsLoading,
    isFetching: false,
    isError: incidentsError,
    refetch: mockRefetch,
  }),
  useMutation: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
  useQueryClient: () => ({
    invalidateQueries: mockInvalidate,
  }),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/dashboard/incidents',
}));

vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({ toast: vi.fn(), success: vi.fn(), error: vi.fn() }),
}));

vi.mock('@/hooks/useListKeyNav', () => ({
  useListKeyNav: () => ({ activeIndex: -1 }),
}));

vi.mock('@/hooks/useUrlFilters', () => ({
  useUrlFilters: () => ({
    filters: { limit: 20, skip: 0 },
    setFilter: vi.fn(),
    setFilters: vi.fn(),
    resetFilters: vi.fn(),
  }),
}));

vi.mock('@/hooks/useTableDensity', () => ({
  useTableDensity: () => ({ isCompact: false, toggle: vi.fn() }),
  DENSITY_CLASSES: {
    compact: { row: 'py-1', cell: 'px-2', text: 'text-xs' },
    comfortable: { row: 'py-3', cell: 'px-4', text: 'text-sm' },
  },
}));

vi.mock('@/hooks/useSavedViews', () => ({
  useSavedViews: () => ({ views: [], save: vi.fn(), remove: vi.fn() }),
}));

vi.mock('@/components/ui/Skeleton', () => ({
  TableSkeleton: () => <div data-testid="table-skeleton">Loading...</div>,
  Skeleton: () => <div data-testid="skeleton" />,
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

vi.mock('@/components/ui/DensityToggle', () => ({
  DensityToggle: () => <div data-testid="density-toggle" />,
}));

vi.mock('@/components/incidents/IncidentRow', () => ({
  IncidentRow: ({ incident }: { incident: Record<string, unknown> }) => (
    <tr data-testid={`incident-row-${incident.id}`}>
      <td>{String(incident.title)}</td>
    </tr>
  ),
  IncidentCard: () => null,
}));

vi.mock('@/components/incidents/ActiveFilterChips', () => ({
  ActiveFilterChips: () => <div data-testid="filter-chips" />,
}));

vi.mock('@/lib/api', () => ({
  listIncidents: vi.fn(),
  bulkUpdateStatus: vi.fn(),
}));

vi.mock('lucide-react', () => ({
  ShieldAlert: () => <span>ShieldAlert</span>,
  ArrowUpDown: () => <span>Sort</span>,
  ArrowUp: () => <span>Up</span>,
  ArrowDown: () => <span>Down</span>,
  X: () => <span>X</span>,
  Download: () => <span>Download</span>,
}));

import IncidentsPage from '@/app/(app)/dashboard/incidents/page';

describe('IncidentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    incidentsLoading = false;
    incidentsError = false;
    incidentsData = undefined;
  });

  it('renders page title', () => {
    incidentsData = { items: [], total: 0 };
    render(<IncidentsPage />);
    expect(screen.getByText('Incidents')).toBeInTheDocument();
  });

  it('renders error state with retry', () => {
    incidentsError = true;
    render(<IncidentsPage />);
    expect(screen.getByTestId('query-error')).toBeInTheDocument();
  });

  it('renders empty state when no incidents', () => {
    incidentsData = { items: [], total: 0 };
    render(<IncidentsPage />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('renders incident rows when data exists', () => {
    incidentsData = {
      items: [
        { id: 'i-1', title: 'PII Detected', severity: 'high', status: 'open', category: 'pii_leak', createdAt: '2024-01-01T00:00:00Z' },
        { id: 'i-2', title: 'Hallucination', severity: 'medium', status: 'resolved', category: 'hallucination', createdAt: '2024-01-02T00:00:00Z' },
      ],
      total: 2,
    };
    render(<IncidentsPage />);
    expect(screen.getByTestId('incident-row-i-1')).toBeInTheDocument();
    expect(screen.getByTestId('incident-row-i-2')).toBeInTheDocument();
  });
});
