import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

const OPEN_MODAL_SELECTOR = [
  '[role="dialog"][aria-modal="true"]',
  '[role="alertdialog"][aria-modal="true"]',
].join(',');

export function hasOpenModal(except: HTMLElement | null = null) {
  return Array.from(document.querySelectorAll<HTMLElement>(OPEN_MODAL_SELECTOR)).some(
    (modal) => modal !== except,
  );
}

function handleModalKeyDown(
  event: KeyboardEvent,
  container: HTMLElement | null,
  onEscape: () => void,
) {
  if (event.key === 'Escape') {
    event.preventDefault();
    onEscape();
    return;
  }

  if (event.key !== 'Tab' || !container) return;

  const focusable = Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
  );
  if (focusable.length === 0) {
    event.preventDefault();
    container.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;

  if (event.shiftKey && (active === first || !container.contains(active))) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && (active === last || !container.contains(active))) {
    event.preventDefault();
    first.focus();
  }
}

export function useModalKeyboardBoundary(
  containerRef: RefObject<HTMLElement>,
  onEscape: () => void,
  active: boolean,
) {
  const onEscapeRef = useRef(onEscape);

  useEffect(() => {
    onEscapeRef.current = onEscape;
  }, [onEscape]);

  useEffect(() => {
    const container = containerRef.current;
    if (!active || !container) return;

    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const handleKeyDown = (event: KeyboardEvent) =>
      handleModalKeyDown(event, container, () => onEscapeRef.current());
    container.addEventListener('keydown', handleKeyDown);
    return () => {
      container.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [active, containerRef]);
}
