import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

let incidentLoading = true;
let incidentData: Record<string, unknown> | undefined;

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'incident-1' }),
  useRouter: () => ({ back: vi.fn() }),
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => {
    if (queryKey[0] === 'incident') {
      return {
        data: incidentData,
        isLoading: incidentLoading,
        isError: false,
        refetch: vi.fn(),
      };
    }
    return { data: undefined, isLoading: false, isError: false };
  },
  useMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

vi.mock('@/lib/api', () => ({
  getIncident: vi.fn(),
  updateIncidentStatus: vi.fn(),
  addIncidentAction: vi.fn(),
}));

vi.mock('@/lib/api/sandboxes', () => ({ getExecution: vi.fn() }));
vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({ success: vi.fn() }),
}));
vi.mock('@/components/incidents/DetectionTimeline', () => ({
  DetectionTimeline: () => <div>Detection timeline</div>,
}));
vi.mock('@/components/incidents/ResponsePlaybook', () => ({
  ResponsePlaybook: () => <div>Response playbook</div>,
}));
vi.mock('@/components/ui/ConfirmDialog', () => ({
  ConfirmDialog: () => null,
}));

import IncidentDetailPage from '@/app/(app)/dashboard/incidents/[id]/page';

describe('IncidentDetailPage', () => {
  let opener: HTMLButtonElement | null = null;

  beforeEach(() => {
    incidentLoading = true;
    incidentData = undefined;
  });

  afterEach(() => {
    opener?.remove();
    opener = null;
  });

  it('keeps hook order stable when loading completes', () => {
    const view = render(<IncidentDetailPage />);
    expect(view.container.querySelector('.animate-spin')).toBeInTheDocument();

    incidentLoading = false;
    incidentData = {
      id: 'incident-1',
      title: 'PII detected',
      severity: 'high',
      status: 'open',
      category: 'pii_leak',
      description: 'Sensitive value detected',
      actionTaken: null,
      proxyRequestId: 'request-1',
      detectorId: 'detector-1',
      sandboxExecutionId: null,
      resolvedAt: null,
      createdAt: '2026-08-27T12:00:00Z',
      updatedAt: '2026-08-27T12:00:00Z',
      actions: [],
    };

    expect(() => view.rerender(<IncidentDetailPage />)).not.toThrow();
    expect(screen.getByRole('heading', { name: 'PII detected' })).toBeInTheDocument();
  });

  it('contains quick-status keyboard focus and restores the opener', () => {
    incidentLoading = false;
    incidentData = {
      id: 'incident-1',
      title: 'PII detected',
      severity: 'high',
      status: 'open',
      category: 'pii_leak',
      description: 'Sensitive value detected',
      actionTaken: null,
      proxyRequestId: 'request-1',
      detectorId: 'detector-1',
      sandboxExecutionId: null,
      resolvedAt: null,
      createdAt: '2026-08-27T12:00:00Z',
      updatedAt: '2026-08-27T12:00:00Z',
      actions: [],
    };
    opener = document.createElement('button');
    document.body.appendChild(opener);
    opener.focus();

    render(<IncidentDetailPage />);
    act(() => window.dispatchEvent(new CustomEvent('keyboard:quick-status')));

    const dialog = screen.getByRole('dialog', { name: 'Set incident status' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('button', { name: /Acknowledged/ })).toHaveFocus();

    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });
    expect(screen.getByRole('button', { name: /Dismissed/ })).toHaveFocus();

    fireEvent.keyDown(dialog, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: 'Set incident status' })).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });
});
