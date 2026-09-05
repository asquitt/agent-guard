'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { hasOpenModal, useModalKeyboardBoundary } from '@/lib/dialog';

const SHORTCUTS = [
  { section: 'Navigation', items: [
    { keys: ['⌘', 'K'], desc: 'Open command palette' },
    { keys: ['?'], desc: 'Show keyboard shortcuts' },
    { keys: ['/'], desc: 'Focus search / filter input' },
  ]},
  { section: 'Go to...', items: [
    { keys: ['G', 'D'], desc: 'Dashboard' },
    { keys: ['G', 'I'], desc: 'Incidents' },
    { keys: ['G', 'A'], desc: 'Analytics' },
    { keys: ['G', 'R'], desc: 'Reviews' },
    { keys: ['G', 'T'], desc: 'Detectors' },
    { keys: ['G', 'L'], desc: 'Alerts' },
    { keys: ['G', 'K'], desc: 'Risk Score' },
    { keys: ['G', 'S'], desc: 'Settings' },
  ]},
  { section: 'List navigation', items: [
    { keys: ['J'], desc: 'Next item' },
    { keys: ['K'], desc: 'Previous item' },
    { keys: ['Enter'], desc: 'Open selected item' },
  ]},
  { section: 'Actions', items: [
    { keys: ['E'], desc: 'Quick status change' },
    { keys: ['Esc'], desc: 'Close dialog / Cancel' },
  ]},
];

const G_ROUTES: Record<string, string> = {
  d: '/dashboard',
  i: '/dashboard/incidents',
  a: '/dashboard/analytics',
  r: '/dashboard/reviews',
  t: '/dashboard/detectors',
  l: '/dashboard/alerts',
  k: '/dashboard/risk-score',
  s: '/dashboard/settings',
};

export function KeyboardShortcuts() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const pendingG = useRef(false);
  const gTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const closeShortcuts = () => setOpen(false);
  useModalKeyboardBoundary(dialogRef, closeShortcuts, open);

  useEffect(() => {
    if (open) closeRef.current?.focus();
  }, [open]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (hasOpenModal(dialogRef.current)) return;

      if (open) {
        if (e.key === '?' || e.key === 'Escape') {
          e.preventDefault();
          setOpen(false);
        }
        return;
      }

      if (e.key === '?' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setOpen((p) => !p);
        return;
      }
      // / to focus search
      if (e.key === '/' && !e.metaKey && !e.ctrlKey) {
        const input = document.querySelector<HTMLInputElement>(
          'input[type="text"][placeholder*="earch"], input[type="text"][placeholder*="ilter"]',
        );
        if (input) {
          e.preventDefault();
          input.focus();
          return;
        }
      }

      // E for quick status change
      if (e.key === 'e' && !e.metaKey && !e.ctrlKey && !pendingG.current) {
        window.dispatchEvent(new CustomEvent('keyboard:quick-status'));
        return;
      }

      // J/K for list navigation
      if (e.key === 'j' || e.key === 'k') {
        window.dispatchEvent(new CustomEvent('keyboard:list-nav', { detail: { direction: e.key === 'j' ? 'next' : 'prev' } }));
        return;
      }

      // G+key two-step combo
      if (e.key === 'g' && !e.metaKey && !e.ctrlKey) {
        pendingG.current = true;
        if (gTimer.current) clearTimeout(gTimer.current);
        gTimer.current = setTimeout(() => { pendingG.current = false; }, 500);
        return;
      }
      if (pendingG.current) {
        pendingG.current = false;
        if (gTimer.current) clearTimeout(gTimer.current);
        const route = G_ROUTES[e.key];
        if (route) {
          e.preventDefault();
          router.push(route);
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (gTimer.current) clearTimeout(gTimer.current);
    };
  }, [open, router]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="keyboard-shortcuts-title"
        tabIndex={-1}
        className="relative w-full max-w-md rounded-xl border border-border bg-popover p-6 shadow-2xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 id="keyboard-shortcuts-title" className="text-sm font-semibold text-foreground">Keyboard Shortcuts</h2>
          <button
            ref={closeRef}
            type="button"
            aria-label="Close keyboard shortcuts"
            onClick={() => setOpen(false)}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            esc
          </button>
        </div>
        <div className="space-y-5">
          {SHORTCUTS.map((section) => (
            <div key={section.section}>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {section.section}
              </p>
              <div className="space-y-2">
                {section.items.map((item) => (
                  <div key={item.desc} className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{item.desc}</span>
                    <div className="flex gap-1">
                      {item.keys.map((key) => (
                        <kbd
                          key={key}
                          className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-foreground"
                        >
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
