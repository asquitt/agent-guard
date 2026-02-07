import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockPush = vi.fn();
const mockLogin = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    isAuthenticated: false,
    isLoading: false,
    user: null,
  }),
}));

import LoginPage from '@/app/(auth)/login/page';

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form with email, password, and submit button', () => {
    render(<LoginPage />);

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('renders register and SSO links', () => {
    render(<LoginPage />);

    expect(screen.getByRole('link', { name: /create one/i })).toHaveAttribute(
      'href',
      '/register',
    );
    expect(screen.getByRole('link', { name: /sign in with sso/i })).toHaveAttribute(
      'href',
      '/login/sso',
    );
  });

  it('calls login with credentials on form submit', async () => {
    mockLogin.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<LoginPage />);

    await user.type(screen.getByLabelText(/email/i), 'user@example.com');
    await user.type(screen.getByLabelText(/password/i), 'secret123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('user@example.com', 'secret123');
    });
  });

  it('displays error message when login fails', async () => {
    const { ApiError } = await import('@/lib/api/client');
    mockLogin.mockRejectedValue(new ApiError(401, 'Invalid credentials'));
    const user = userEvent.setup();

    render(<LoginPage />);

    await user.type(screen.getByLabelText(/email/i), 'bad@example.com');
    await user.type(screen.getByLabelText(/password/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });
});
