import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockLogout = vi.fn();

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { name: 'Test User', email: 'test@example.com' },
    organization: { name: 'Test Org' },
    isAuthenticated: true,
    logout: mockLogout,
  }),
}));

import { Header } from '@/components/layout/Header';

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders organization name', () => {
    render(<Header />);

    expect(screen.getByText('Test Org')).toBeInTheDocument();
  });

  it('renders user name', () => {
    render(<Header />);

    expect(screen.getByText('Test User')).toBeInTheDocument();
  });

  it('renders user initial avatar', () => {
    render(<Header />);

    expect(screen.getByText('T')).toBeInTheDocument();
  });

  it('shows sign out button in dropdown menu', async () => {
    const user = userEvent.setup();
    render(<Header />);

    // Click the user menu button to open dropdown
    await user.click(screen.getByText('Test User'));

    expect(screen.getByText('Sign out')).toBeInTheDocument();
  });

  it('calls logout when sign out is clicked', async () => {
    const user = userEvent.setup();
    render(<Header />);

    await user.click(screen.getByText('Test User'));
    await user.click(screen.getByText('Sign out'));

    expect(mockLogout).toHaveBeenCalled();
  });
});
