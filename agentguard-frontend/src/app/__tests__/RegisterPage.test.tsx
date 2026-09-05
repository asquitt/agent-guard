import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import RegisterPage, {
  metadata as registerMetadata,
} from '@/app/(auth)/register/page';

describe('RegisterPage archive posture', () => {
  it('fails closed with the authoritative mothballed status', () => {
    const { container } = render(<RegisterPage />);

    expect(
      screen.getByRole('heading', { name: 'Registration unavailable' }),
    ).toBeInTheDocument();
    expect(container.textContent).toContain(
      'AgentGuard is mothballed as a standalone product',
    );
    expect(container.textContent).toContain(
      'No account or workspace can be created from this preserved route.',
    );
  });

  it('renders no registration controls or acquisition links', () => {
    const { container } = render(<RegisterPage />);

    expect(container.querySelector('form')).toBeNull();
    expect(container.querySelector('input')).toBeNull();
    expect(container.querySelector('button')).toBeNull();
    expect(container.querySelector('a[href="/pricing"]')).toBeNull();
    expect(screen.getByRole('link', { name: 'View archived project' })).toHaveAttribute(
      'href',
      '/',
    );
    expect(screen.getByRole('link', { name: 'Existing account sign in' })).toHaveAttribute(
      'href',
      '/login',
    );
  });

  it('keeps registration metadata out of search indexes', () => {
    expect(registerMetadata.robots).toMatchObject({ index: false, follow: false });
    expect(JSON.stringify(registerMetadata)).toContain('mothballed');
  });
});
