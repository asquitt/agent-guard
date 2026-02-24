import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

let mockQueryData: unknown = null;
let mockIsLoading = false;

vi.mock('@tanstack/react-query', () => ({
  useQuery: ({ queryKey }: { queryKey: unknown[] }) => ({
    data: mockQueryData,
    isLoading: mockIsLoading,
  }),
}));

vi.mock('@/lib/api', () => ({
  getDetectionEfficacy: vi.fn(),
}));

import { DetectionEfficacySection } from '../dashboard/DetectionEfficacy';

describe('DetectionEfficacySection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockQueryData = null;
    mockIsLoading = false;
  });

  it('renders section heading', () => {
    render(<DetectionEfficacySection />);
    expect(screen.getByText('Detection Efficacy')).toBeInTheDocument();
  });

  it('renders day selector buttons', () => {
    render(<DetectionEfficacySection />);
    expect(screen.getByText('7d')).toBeInTheDocument();
    expect(screen.getByText('30d')).toBeInTheDocument();
    expect(screen.getByText('90d')).toBeInTheDocument();
  });

  it('shows loading spinner when loading', () => {
    mockIsLoading = true;
    const { container } = render(<DetectionEfficacySection />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows empty message when no data', () => {
    mockQueryData = null;
    render(<DetectionEfficacySection />);
    expect(screen.getByText('No detection data for this period')).toBeInTheDocument();
  });

  it('shows empty message when categories empty', () => {
    mockQueryData = { categories: [], overallFalsePositiveRate: 0 };
    render(<DetectionEfficacySection />);
    expect(screen.getByText('No detection data for this period')).toBeInTheDocument();
  });

  it('renders overall false positive rate', () => {
    mockQueryData = {
      categories: [
        { category: 'pii_leak', total: 100, resolved: 80, dismissed: 5, falsePositiveRate: 0.05, meanTimeToResolveHours: 2.3 },
      ],
      overallFalsePositiveRate: 0.05,
    };
    render(<DetectionEfficacySection />);
    // "5.0%" appears in both the overall card and the per-category table
    const matches = screen.getAllByText('5.0%');
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Overall False Positive Rate')).toBeInTheDocument();
  });

  it('renders total detections count', () => {
    mockQueryData = {
      categories: [
        { category: 'pii_leak', total: 50, resolved: 40, dismissed: 3, falsePositiveRate: 0.06, meanTimeToResolveHours: 1.5 },
        { category: 'compliance', total: 30, resolved: 25, dismissed: 2, falsePositiveRate: 0.07, meanTimeToResolveHours: 3.0 },
      ],
      overallFalsePositiveRate: 0.065,
    };
    render(<DetectionEfficacySection />);
    expect(screen.getByText('80')).toBeInTheDocument(); // 50 + 30
    expect(screen.getByText('Total Detections')).toBeInTheDocument();
  });

  it('renders category table with labels', () => {
    mockQueryData = {
      categories: [
        { category: 'pii_leak', total: 100, resolved: 80, dismissed: 5, falsePositiveRate: 0.05, meanTimeToResolveHours: 2.3 },
      ],
      overallFalsePositiveRate: 0.05,
    };
    render(<DetectionEfficacySection />);
    expect(screen.getByText('PII Leak')).toBeInTheDocument();
    // "100" and "80" may appear in both summary and table, so use getAllByText
    expect(screen.getAllByText('100').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('80').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('2.3h')).toBeInTheDocument();
  });

  it('renders dash for null MTTR', () => {
    mockQueryData = {
      categories: [
        { category: 'compliance', total: 10, resolved: 5, dismissed: 1, falsePositiveRate: 0.1, meanTimeToResolveHours: null },
      ],
      overallFalsePositiveRate: 0.1,
    };
    render(<DetectionEfficacySection />);
    expect(screen.getByText('-')).toBeInTheDocument();
  });

  it('applies green color for low FP rate', () => {
    mockQueryData = {
      categories: [
        { category: 'pii_leak', total: 10, resolved: 9, dismissed: 0, falsePositiveRate: 0.0, meanTimeToResolveHours: 1 },
      ],
      overallFalsePositiveRate: 0.05,
    };
    const { container } = render(<DetectionEfficacySection />);
    const fpRate = container.querySelector('.text-green-600');
    expect(fpRate).toBeInTheDocument();
  });

  it('day selector buttons are clickable', async () => {
    const user = userEvent.setup();
    render(<DetectionEfficacySection />);
    const btn7d = screen.getByText('7d');
    await user.click(btn7d);
    // Verify 7d button gets active style (has shadow-sm)
    expect(btn7d).toHaveClass('bg-card');
  });
});
