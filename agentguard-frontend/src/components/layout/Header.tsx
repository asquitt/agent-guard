'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useTheme } from 'next-themes';
import { Sun, Moon, Search, Menu } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useSidebar } from '@/hooks/useSidebar';

export function Header() {
  const { user, organization, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const { toggle: toggleSidebar } = useSidebar();
  const [mounted, setMounted] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => setMounted(true), []);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false);
        triggerRef.current?.focus();
      }
    },
    [],
  );

  return (
    <header className="fixed left-0 right-0 top-0 z-10 flex h-14 items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-sm md:left-64 md:px-6" role="banner">
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground md:hidden"
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
        <span className="text-sm text-muted-foreground">
          {organization?.name ?? 'Organization'}
        </span>
        <button
          onClick={() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))}
          className="hidden items-center gap-2 rounded-md border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted sm:flex"
        >
          <Search className="h-3 w-3" />
          Search...
          <kbd className="ml-2 rounded border border-border bg-background px-1 py-0.5 text-[10px] font-medium">
            ⌘K
          </kbd>
        </button>
      </div>

      <div className="flex items-center gap-2">
        {mounted && (
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        )}

      <div className="relative" ref={menuRef} onKeyDown={handleKeyDown}>
        <button
          ref={triggerRef}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          aria-label="User menu"
          className="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-primary/20 text-xs font-medium text-primary" aria-hidden="true">
            {user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
          </span>
          <span className="hidden sm:inline">{user?.name ?? 'User'}</span>
        </button>

        {menuOpen && (
          <div className="absolute right-0 top-full mt-1 w-48 rounded-lg border border-border bg-popover py-1 shadow-lg" role="menu" aria-label="User actions">
            <div className="border-b border-border px-4 py-2" role="none">
              <p className="text-sm font-medium text-foreground">{user?.name}</p>
              <p className="text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <Link
              href="/dashboard/settings/profile"
              role="menuitem"
              onClick={() => setMenuOpen(false)}
              className="block w-full px-4 py-2 text-left text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              Profile
            </Link>
            <Link
              href="/dashboard/settings"
              role="menuitem"
              onClick={() => setMenuOpen(false)}
              className="block w-full px-4 py-2 text-left text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              Settings
            </Link>
            <button
              role="menuitem"
              onClick={() => {
                setMenuOpen(false);
                logout();
              }}
              className="w-full px-4 py-2 text-left text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
      </div>
    </header>
  );
}
