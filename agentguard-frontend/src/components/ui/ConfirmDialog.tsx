'use client';

import { useEffect, useRef } from 'react';
import { clsx } from 'clsx';
import { useModalKeyboardBoundary } from '@/lib/dialog';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  useModalKeyboardBoundary(dialogRef, onCancel, open);

  // Focus cancel button when dialog opens (safer default)
  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        className="absolute inset-0 bg-black/50"
        onClick={onCancel}
      />
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-desc"
        tabIndex={-1}
        className="relative w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-xl"
      >
        <h2 id="confirm-title" className="text-lg font-semibold text-foreground">
          {title}
        </h2>
        <p id="confirm-desc" className="mt-2 text-sm text-muted-foreground">
          {description}
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            ref={cancelRef}
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={clsx(
              'rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50',
              variant === 'danger'
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-primary hover:bg-primary/90',
            )}
          >
            {loading ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
