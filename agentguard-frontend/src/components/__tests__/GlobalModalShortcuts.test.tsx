import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('next-themes', () => ({
  useTheme: () => ({ theme: 'light', setTheme: vi.fn() }),
}));

import { CommandPalette } from '@/components/ui/CommandPalette';
import { KeyboardShortcuts } from '@/components/ui/KeyboardShortcuts';

describe('global modal shortcuts', () => {
  const onQuickStatus = vi.fn();

  afterEach(() => {
    window.removeEventListener('keyboard:quick-status', onQuickStatus);
    onQuickStatus.mockReset();
  });

  it('keeps one modal active and suppresses background shortcuts', async () => {
    window.addEventListener('keyboard:quick-status', onQuickStatus);
    render(
      <>
        <CommandPalette />
        <KeyboardShortcuts />
      </>,
    );

    fireEvent.keyDown(document, { key: '?' });
    expect(screen.getByRole('dialog', { name: 'Keyboard Shortcuts' })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'e' });
    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    expect(onQuickStatus).not.toHaveBeenCalled();
    expect(screen.getAllByRole('dialog')).toHaveLength(1);
    expect(screen.queryByRole('dialog', { name: 'Command palette' })).not.toBeInTheDocument();

    fireEvent.keyDown(document, { key: '?' });
    expect(screen.queryByRole('dialog', { name: 'Keyboard Shortcuts' })).not.toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    expect(screen.getByRole('dialog', { name: 'Command palette' })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: '?' });
    expect(screen.getAllByRole('dialog')).toHaveLength(1);
    expect(screen.queryByRole('dialog', { name: 'Keyboard Shortcuts' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Keyboard shortcuts' }));
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: 'Keyboard Shortcuts' })).toBeInTheDocument();
    });
    expect(screen.getAllByRole('dialog')).toHaveLength(1);
    expect(screen.queryByRole('dialog', { name: 'Command palette' })).not.toBeInTheDocument();
  });
});
