import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockClearFeed = vi.fn();
let mockItems: Array<{
  id: string;
  type: string;
  title: string;
  description?: string;
  severity?: string;
  timestamp: string;
}> = [];

vi.mock('@/hooks/useActivityFeed', () => ({
  useActivityFeed: () => ({ items: mockItems, clearFeed: mockClearFeed }),
}));

vi.mock('@/lib/format', () => ({
  timeAgo: (date: string) => '2m ago',
}));

import { ActivityFeed } from '../dashboard/ActivityFeed';

describe('ActivityFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockItems = [];
  });

  it('renders empty state when no items', () => {
    render(<ActivityFeed />);
    expect(screen.getByText('No recent activity')).toBeInTheDocument();
    expect(screen.getByText('Events will appear here in real-time')).toBeInTheDocument();
  });

  it('renders header with Live Activity title', () => {
    render(<ActivityFeed />);
    expect(screen.getByText('Live Activity')).toBeInTheDocument();
  });

  it('does not show clear button when empty', () => {
    render(<ActivityFeed />);
    expect(screen.queryByText('Clear')).not.toBeInTheDocument();
  });

  it('does not show count badge when empty', () => {
    render(<ActivityFeed />);
    // Count badge only renders when items.length > 0
    const badges = screen.queryAllByText('0');
    expect(badges).toHaveLength(0);
  });

  it('renders items when present', () => {
    mockItems = [
      {
        id: '1',
        type: 'incident.new',
        title: 'New incident detected',
        description: 'PII leak in response',
        severity: 'critical',
        timestamp: '2024-01-01T00:00:00Z',
      },
    ];
    render(<ActivityFeed />);
    expect(screen.getByText('New incident detected')).toBeInTheDocument();
    expect(screen.getByText('PII leak in response')).toBeInTheDocument();
  });

  it('shows item count badge', () => {
    mockItems = [
      { id: '1', type: 'incident.new', title: 'A', timestamp: '2024-01-01T00:00:00Z' },
      { id: '2', type: 'alert.sent', title: 'B', timestamp: '2024-01-01T00:00:00Z' },
    ];
    render(<ActivityFeed />);
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('shows clear button when items present', () => {
    mockItems = [
      { id: '1', type: 'incident.new', title: 'A', timestamp: '2024-01-01T00:00:00Z' },
    ];
    render(<ActivityFeed />);
    expect(screen.getByText('Clear')).toBeInTheDocument();
  });

  it('calls clearFeed when clear button clicked', async () => {
    mockItems = [
      { id: '1', type: 'incident.new', title: 'A', timestamp: '2024-01-01T00:00:00Z' },
    ];
    const user = userEvent.setup();
    render(<ActivityFeed />);
    await user.click(screen.getByText('Clear'));
    expect(mockClearFeed).toHaveBeenCalledOnce();
  });

  it('renders time ago for each item', () => {
    mockItems = [
      { id: '1', type: 'incident.new', title: 'A', timestamp: '2024-01-01T00:00:00Z' },
    ];
    render(<ActivityFeed />);
    expect(screen.getByText('2m ago')).toBeInTheDocument();
  });

  it('renders severity dot when item has severity', () => {
    mockItems = [
      { id: '1', type: 'incident.new', title: 'A', severity: 'critical', timestamp: '2024-01-01T00:00:00Z' },
    ];
    const { container } = render(<ActivityFeed />);
    const dot = container.querySelector('[title="critical"]');
    expect(dot).toBeInTheDocument();
  });
});
