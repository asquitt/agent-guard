'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { hasOpenModal, useModalKeyboardBoundary } from '@/lib/dialog';
import {
  LayoutDashboard,
  BarChart3,
  ShieldCheck,
  AlertTriangle,
  Bot,
  Search,
  Eye,
  Bell,
  Ghost,
  Route,
  MessageSquare,
  Shield,
  Target,
  Box,
  FlaskConical,
  Key,
  CreditCard,
  ClipboardCheck,
  Settings,
  Layers,
  User,
  Sun,
  Moon,
  Keyboard,
  type LucideIcon,
} from 'lucide-react';

interface CommandItem {
  id: string;
  label: string;
  href?: string;
  action?: () => void;
  icon: LucideIcon;
  section: string;
  keywords?: string[];
}

const COMMANDS: CommandItem[] = [
  { id: 'dashboard', label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, section: 'Navigation' },
  { id: 'analytics', label: 'Analytics', href: '/dashboard/analytics', icon: BarChart3, section: 'Navigation' },
  { id: 'risk-score', label: 'Risk Score', href: '/dashboard/risk-score', icon: ShieldCheck, section: 'Navigation', keywords: ['risk', 'grade', 'posture', 'score'] },
  { id: 'incidents', label: 'Incidents', href: '/dashboard/incidents', icon: AlertTriangle, section: 'Security', keywords: ['alert', 'issue'] },
  { id: 'agents', label: 'Agents', href: '/dashboard/agents', icon: Bot, section: 'Security' },
  { id: 'detectors', label: 'Detectors', href: '/dashboard/detectors', icon: Search, section: 'Security', keywords: ['detection', 'rules'] },
  { id: 'reviews', label: 'Reviews', href: '/dashboard/reviews', icon: Eye, section: 'Security', keywords: ['queue', 'approval'] },
  { id: 'alerts', label: 'Alert Destinations', href: '/dashboard/alerts', icon: Bell, section: 'Security', keywords: ['slack', 'pagerduty', 'webhook'] },
  { id: 'sandboxes', label: 'Sandboxes', href: '/dashboard/sandboxes', icon: Box, section: 'Security' },
  { id: 'model-registry', label: 'Model Registry', href: '/dashboard/model-registry', icon: Layers, section: 'Security', keywords: ['ai', 'llm', 'model'] },
  { id: 'shadow-ai', label: 'Shadow AI', href: '/dashboard/shadow-ai', icon: Ghost, section: 'Intelligence' },
  { id: 'traces', label: 'Traces', href: '/dashboard/traces', icon: Route, section: 'Intelligence', keywords: ['span', 'trace'] },
  { id: 'conversations', label: 'Conversations', href: '/dashboard/conversations', icon: MessageSquare, section: 'Intelligence' },
  { id: 'threat-intel', label: 'Threat Intel', href: '/dashboard/threat-intel', icon: Shield, section: 'Intelligence', keywords: ['threat', 'ioc'] },
  { id: 'red-team', label: 'Red Team', href: '/dashboard/red-team', icon: Target, section: 'Intelligence', keywords: ['test', 'attack'] },
  { id: 'playground', label: 'Playground', href: '/dashboard/playground', icon: FlaskConical, section: 'Tools', keywords: ['test', 'try'] },
  { id: 'api-keys', label: 'API Keys', href: '/dashboard/api-keys', icon: Key, section: 'Tools', keywords: ['key', 'token'] },
  { id: 'billing', label: 'Billing', href: '/dashboard/billing', icon: CreditCard, section: 'Settings', keywords: ['plan', 'subscription', 'payment'] },
  { id: 'compliance', label: 'Compliance', href: '/dashboard/compliance', icon: ClipboardCheck, section: 'Settings', keywords: ['audit', 'report'] },
  { id: 'settings', label: 'Settings', href: '/dashboard/settings', icon: Settings, section: 'Settings' },
  { id: 'profile', label: 'Profile', href: '/dashboard/settings/profile', icon: User, section: 'Settings', keywords: ['account', 'name'] },
  { id: 'notifications', label: 'Notification Preferences', href: '/dashboard/settings/notifications', icon: Bell, section: 'Settings', keywords: ['email', 'digest'] },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const closePalette = useCallback(() => setOpen(false), []);
  useModalKeyboardBoundary(dialogRef, closePalette, open);

  // Build action commands dynamically (theme depends on current state)
  const actionCommands: CommandItem[] = useMemo(() => [
    {
      id: 'toggle-theme',
      label: theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode',
      icon: theme === 'dark' ? Sun : Moon,
      section: 'Actions',
      keywords: ['theme', 'dark', 'light', 'mode'],
      action: () => setTheme(theme === 'dark' ? 'light' : 'dark'),
    },
    {
      id: 'show-shortcuts',
      label: 'Keyboard shortcuts',
      icon: Keyboard,
      section: 'Actions',
      keywords: ['shortcut', 'hotkey', 'keys'],
      action: () => {
        window.setTimeout(
          () => document.dispatchEvent(new KeyboardEvent('keydown', { key: '?' })),
          0,
        );
      },
    },
  ], [theme, setTheme]);

  const allCommands = useMemo(() => [...COMMANDS, ...actionCommands], [actionCommands]);

  // Cmd+K / Ctrl+K to open
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (hasOpenModal(dialogRef.current)) return;

      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (open && e.key === 'Escape') {
        setOpen(false);
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  const filtered = useMemo(() => {
    if (!query.trim()) return allCommands;
    const q = query.toLowerCase();
    return allCommands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(q) ||
        cmd.section.toLowerCase().includes(q) ||
        cmd.keywords?.some((kw) => kw.includes(q)),
    );
  }, [query, allCommands]);

  // Group by section
  const grouped = useMemo(() => {
    const groups: { section: string; items: CommandItem[] }[] = [];
    const seen = new Set<string>();
    for (const item of filtered) {
      if (!seen.has(item.section)) {
        seen.add(item.section);
        groups.push({ section: item.section, items: [] });
      }
      groups.find((g) => g.section === item.section)!.items.push(item);
    }
    return groups;
  }, [filtered]);

  const executeCommand = useCallback(
    (cmd: CommandItem) => {
      setOpen(false);
      if (cmd.action) {
        cmd.action();
      } else if (cmd.href) {
        router.push(cmd.href);
      }
    },
    [router],
  );

  // Keyboard navigation
  function handleInputKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      e.preventDefault();
      executeCommand(filtered[selectedIndex]);
    }
  }

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${selectedIndex}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  if (!open) return null;

  let flatIndex = -1;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* Palette */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        tabIndex={-1}
        className="relative w-full max-w-lg rounded-xl border border-border bg-popover shadow-2xl"
      >
        {/* Search input */}
        <div className="flex items-center gap-3 border-b border-border px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            ref={inputRef}
            aria-label="Search pages"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={handleInputKeyDown}
            placeholder="Search pages..."
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
          <kbd className="hidden rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground sm:inline">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-80 overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-muted-foreground">
              No results found
            </p>
          ) : (
            grouped.map((group) => (
              <div key={group.section}>
                <p className="px-4 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {group.section}
                </p>
                {group.items.map((item) => {
                  flatIndex++;
                  const idx = flatIndex;
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      data-index={idx}
                      onClick={() => executeCommand(item)}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`flex w-full items-center gap-3 px-4 py-2 text-sm transition-colors ${
                        idx === selectedIndex
                          ? 'bg-accent text-foreground'
                          : 'text-muted-foreground hover:bg-accent/50'
                      }`}
                    >
                      <Icon className="h-4 w-4 flex-shrink-0" />
                      {item.label}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 border-t border-border px-4 py-2 text-[10px] text-muted-foreground">
          <span><kbd className="rounded border border-border bg-muted px-1 py-0.5 font-mono">↑↓</kbd> Navigate</span>
          <span><kbd className="rounded border border-border bg-muted px-1 py-0.5 font-mono">↵</kbd> Open</span>
          <span><kbd className="rounded border border-border bg-muted px-1 py-0.5 font-mono">esc</kbd> Close</span>
        </div>
      </div>
    </div>
  );
}
