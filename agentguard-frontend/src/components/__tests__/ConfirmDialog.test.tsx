import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

describe('ConfirmDialog focus boundary', () => {
  it('keeps keyboard focus inside the modal and makes the backdrop untabbable', () => {
    const onCancel = vi.fn();
    const { container } = render(
      <ConfirmDialog
        open
        title="Delete destination?"
        description="This removes the destination."
        onCancel={onCancel}
        onConfirm={vi.fn()}
      />,
    );

    const dialog = screen.getByRole('alertdialog');
    const cancel = screen.getByRole('button', { name: 'Cancel' });
    const confirm = screen.getByRole('button', { name: 'Confirm' });
    const backdrop = container.querySelector<HTMLButtonElement>('button[aria-hidden="true"]');

    expect(cancel).toHaveFocus();
    expect(backdrop).toHaveAttribute('tabindex', '-1');

    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });
    expect(confirm).toHaveFocus();

    fireEvent.keyDown(dialog, { key: 'Tab' });
    expect(cancel).toHaveFocus();

    fireEvent.keyDown(dialog, { key: 'Escape' });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
