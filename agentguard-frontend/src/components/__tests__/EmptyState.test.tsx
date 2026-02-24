import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Activity } from 'lucide-react';

vi.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

import { EmptyState } from '../ui/EmptyState';

describe('EmptyState', () => {
  it('renders title', () => {
    render(<EmptyState title="No incidents found" />);
    expect(screen.getByText('No incidents found')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(<EmptyState title="Empty" description="Nothing to see here" />);
    expect(screen.getByText('Nothing to see here')).toBeInTheDocument();
  });

  it('does not render description when omitted', () => {
    render(<EmptyState title="Empty" />);
    expect(screen.queryByText('Nothing to see here')).not.toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    const { container } = render(<EmptyState title="Empty" icon={Activity} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('renders action link when action has href', () => {
    render(
      <EmptyState
        title="Empty"
        action={{ label: 'Create Detector', href: '/detectors/new' }}
      />,
    );
    const link = screen.getByText('Create Detector');
    expect(link).toBeInTheDocument();
    expect(link.closest('a')).toHaveAttribute('href', '/detectors/new');
  });

  it('renders action button when action has onClick', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <EmptyState
        title="Empty"
        action={{ label: 'Refresh', onClick }}
      />,
    );
    await user.click(screen.getByText('Refresh'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('renders hint links', () => {
    render(
      <EmptyState
        title="Empty"
        hints={[
          { label: 'View docs', href: '/docs' },
          { label: 'Get help', href: '/help' },
        ]}
      />,
    );
    const docsLink = screen.getByText(/View docs/);
    expect(docsLink.closest('a')).toHaveAttribute('href', '/docs');
    const helpLink = screen.getByText(/Get help/);
    expect(helpLink.closest('a')).toHaveAttribute('href', '/help');
  });

  it('does not render hints section when empty', () => {
    const { container } = render(<EmptyState title="Empty" hints={[]} />);
    expect(container.querySelectorAll('a')).toHaveLength(0);
  });
});
