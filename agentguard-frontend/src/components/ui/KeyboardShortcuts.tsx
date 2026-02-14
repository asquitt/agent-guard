'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

const SHORTCUTS = [
  { section: 'Navigation', items: [
    { keys: ['⌘', 'K'], desc: 'Open command palette' },
    { keys: ['?'], desc: 'Show keyboard shortcuts' },
  ]},
  { section: 'Go to...', items: [
    { keys: ['G', 'D'], desc: 'Go to Dashboard' },
    { keys: ['G', 'I'], desc: 'Go to Incidents' },
    { keys: ['G', 'A'], desc: 'Go to Analytics' },
    { keys: ['G', 'S'], desc: 'Go to Settings' },
  ]},
  { section: 'Actions', items: [
    { keys: ['Esc'], desc: 'Close dialog / Cancel' },
  ]},
];

const G_ROUTES: Record<string, string> = {
  d: '/dashboard',
  i: '/dashboard/incidents',
  a: '/dashboard/analytics',
  s: '/dashboard/settings',
};

export function KeyboardShortcuts() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const pendingG = useRef(false);
  const gTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === '?' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setOpen((p) => !p);
        return;
      }
      if (e.key === 'Escape') { setOpen(false); return; }

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
  }, [router]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-md rounded-xl border border-border bg-popover p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Keyboard Shortcuts</h2>
          <button
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
