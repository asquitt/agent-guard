import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockMutate = vi.fn();
const mockInvalidateQueries = vi.fn();
const mockSuccess = vi.fn();

vi.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: ({ mutationFn }: { mutationFn: (s: string) => Promise<unknown> }) => ({
    mutate: mockMutate,
    isPending: false,
  }),
  useQueryClient: () => ({
    invalidateQueries: mockInvalidateQueries,
  }),
}));

vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({
    success: mockSuccess,
    error: vi.fn(),
    warning: vi.fn(),
    toast: vi.fn(),
  }),
}));

vi.mock('@/lib/format', () => ({
  timeAgo: () => '5m ago',
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
}));

import { IncidentRow, IncidentCard } from '../incidents/IncidentRow';
import type { Incident } from '@/types';

const mockIncident: Incident = {
  id: 'inc-1',
  title: 'PII Detected in Output',
  category: 'pii_leak',
  severity: 'critical',
  status: 'open',
  description: 'SSN found in response',
  createdAt: '2024-01-15T10:30:00Z',
  updatedAt: '2024-01-15T10:30:00Z',
  actionTaken: 'redacted',
  detectorId: 'det-1',
  proxyRequestId: 'req-1',
  sandboxExecutionId: null,
  resolvedAt: null,
};

function renderRow(overrides: Partial<Parameters<typeof IncidentRow>[0]> = {}) {
  return render(
    <table>
      <tbody>
        <IncidentRow
          incident={mockIncident}
          cellClass="px-4 py-2"
          selected={false}
          focused={false}
          onToggle={vi.fn()}
          {...overrides}
        />
      </tbody>
    </table>,
  );
}

describe('IncidentRow', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders incident title as link', () => {
    renderRow();
    const link = screen.getByText('PII Detected in Output');
    expect(link.closest('a')).toHaveAttribute('href', '/dashboard/incidents/inc-1');
  });

  it('renders category with underscores replaced', () => {
    renderRow();
    expect(screen.getByText('pii leak')).toBeInTheDocument();
  });

  it('renders severity badge', () => {
    renderRow();
    expect(screen.getByText('critical')).toBeInTheDocument();
  });

  it('renders status dropdown with current value', () => {
    renderRow();
    const select = screen.getByDisplayValue('open');
    expect(select).toBeInTheDocument();
  });

  it('renders all status options', () => {
    renderRow();
    expect(screen.getByText('open')).toBeInTheDocument();
    expect(screen.getByText('acknowledged')).toBeInTheDocument();
    expect(screen.getByText('resolved')).toBeInTheDocument();
    expect(screen.getByText('dismissed')).toBeInTheDocument();
  });

  it('renders time ago', () => {
    renderRow();
    expect(screen.getByText('5m ago')).toBeInTheDocument();
  });

  it('renders checkbox', () => {
    renderRow();
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('checkbox reflects selected state', () => {
    renderRow({ selected: true });
    expect(screen.getByRole('checkbox')).toBeChecked();
  });

  it('calls onToggle when checkbox clicked', async () => {
    const onToggle = vi.fn();
    const user = userEvent.setup();
    renderRow({ onToggle });
    await user.click(screen.getByRole('checkbox'));
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('calls mutate when status dropdown changes', async () => {
    const user = userEvent.setup();
    renderRow();
    const select = screen.getByDisplayValue('open');
    await user.selectOptions(select, 'resolved');
    expect(mockMutate).toHaveBeenCalledWith('resolved');
  });
});

describe('IncidentCard', () => {
  it('renders incident title', () => {
    render(<IncidentCard incident={mockIncident} />);
    expect(screen.getByText('PII Detected in Output')).toBeInTheDocument();
  });

  it('renders as a link to incident detail', () => {
    render(<IncidentCard incident={mockIncident} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/dashboard/incidents/inc-1');
  });

  it('renders severity badge', () => {
    render(<IncidentCard incident={mockIncident} />);
    expect(screen.getByText('critical')).toBeInTheDocument();
  });

  it('renders category and status', () => {
    render(<IncidentCard incident={mockIncident} />);
    expect(screen.getByText('pii leak')).toBeInTheDocument();
    expect(screen.getByText('open')).toBeInTheDocument();
  });

  it('renders time ago', () => {
    render(<IncidentCard incident={mockIncident} />);
    expect(screen.getByText('5m ago')).toBeInTheDocument();
  });
});
