import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AnalyticsSkeleton, DashboardSkeleton, Skeleton, TableSkeleton } from '../ui/Skeleton';

describe('Skeleton', () => {
  it('renders with animate-pulse class', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass('animate-pulse');
  });

  it('applies custom className', () => {
    const { container } = render(<Skeleton className="h-4 w-24" />);
    expect(container.firstChild).toHaveClass('h-4', 'w-24');
  });

  it('applies custom style', () => {
    const { container } = render(<Skeleton style={{ height: '50%' }} />);
    expect(container.firstChild).toHaveStyle({ height: '50%' });
  });
});

describe('DashboardSkeleton', () => {
  it('renders 4 metric card skeletons', () => {
    const { container } = render(<DashboardSkeleton />);
    const cards = container.querySelectorAll('.rounded-xl.border');
    // 4 metric cards + 1 table container = at least 5
    expect(cards.length).toBeGreaterThanOrEqual(5);
  });

  it('renders 5 table row skeletons', () => {
    const { container } = render(<DashboardSkeleton />);
    const rows = container.querySelectorAll('.divide-y > div');
    expect(rows.length).toBe(5);
  });
});

describe('TableSkeleton', () => {
  it('renders default 8 rows + 1 header', () => {
    const { container } = render(<TableSkeleton />);
    const allRows = container.querySelectorAll('.divide-y > div');
    expect(allRows.length).toBe(9); // 1 header + 8 rows
  });

  it('renders custom row and column count', () => {
    const { container } = render(<TableSkeleton rows={3} cols={4} />);
    const allRows = container.querySelectorAll('.divide-y > div');
    expect(allRows.length).toBe(4); // 1 header + 3 rows
    // Each row (including header) should have 4 skeleton cells
    const firstRow = allRows[0];
    expect(firstRow.querySelectorAll('.animate-pulse').length).toBe(4);
  });
});

describe('AnalyticsSkeleton', () => {
  it('renders 4 summary card skeletons', () => {
    const { container } = render(<AnalyticsSkeleton />);
    const summaryCards = container.querySelectorAll('.grid-cols-4 > div');
    expect(summaryCards.length).toBe(4);
  });

  it('renders chart placeholder bars', () => {
    const { container } = render(<AnalyticsSkeleton />);
    const chartBars = container.querySelectorAll('.items-end .animate-pulse');
    expect(chartBars.length).toBe(20);
  });
});
