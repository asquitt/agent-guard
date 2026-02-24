import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { QueryError } from '../ui/QueryError';

describe('QueryError', () => {
  it('renders default error message', () => {
    render(<QueryError />);
    expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument();
  });

  it('renders custom error message', () => {
    render(<QueryError message="Network error" />);
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('renders "Failed to load data" heading', () => {
    render(<QueryError />);
    expect(screen.getByText('Failed to load data')).toBeInTheDocument();
  });

  it('renders retry button when onRetry is provided', () => {
    render(<QueryError onRetry={() => {}} />);
    expect(screen.getByText('Try again')).toBeInTheDocument();
  });

  it('does not render retry button when onRetry is omitted', () => {
    render(<QueryError />);
    expect(screen.queryByText('Try again')).not.toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<QueryError onRetry={onRetry} />);

    await user.click(screen.getByText('Try again'));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
