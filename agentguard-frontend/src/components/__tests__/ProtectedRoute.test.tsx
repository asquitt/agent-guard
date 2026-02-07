import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockReplace = vi.fn();
let mockAuthState = {
  isAuthenticated: true,
  isLoading: false,
  user: null,
  organization: null,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  fetchMe: vi.fn(),
};

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockAuthState,
}));

import { ProtectedRoute } from '@/components/layout/ProtectedRoute';

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthState = {
      isAuthenticated: true,
      isLoading: false,
      user: null,
      organization: null,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      fetchMe: vi.fn(),
    };
  });

  it('renders children when authenticated', () => {
    mockAuthState.isAuthenticated = true;
    mockAuthState.isLoading = false;

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>,
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    mockAuthState.isAuthenticated = false;
    mockAuthState.isLoading = false;

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>,
    );

    expect(mockReplace).toHaveBeenCalledWith('/login');
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('shows loading spinner while auth is loading', () => {
    mockAuthState.isAuthenticated = false;
    mockAuthState.isLoading = true;

    const { container } = render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>,
    );

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });
});
