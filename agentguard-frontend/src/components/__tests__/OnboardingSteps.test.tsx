import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import OnboardingPage from '@/app/(app)/onboarding/page';

describe('onboarding contract', () => {
  it('renders a static archive boundary without setup actions', () => {
    render(<OnboardingPage />);

    expect(screen.getByRole('heading', { name: /onboarding is unavailable/i })).toBeInTheDocument();
    expect(screen.getByText(/mothballed as a standalone product/i)).toBeInTheDocument();
    expect(screen.getByText(/does not create proxy endpoints or api keys/i)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.queryByText(/send test request/i)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /return to dashboard/i })).toHaveAttribute('href', '/dashboard');
    expect(screen.getByRole('link', { name: /view archive status/i })).toHaveAttribute('href', '/status');
  });
});
