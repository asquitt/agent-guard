'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Logo from '@/components/ui/Logo';
import { clsx } from 'clsx';
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
  type LucideIcon,
} from 'lucide-react';

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: 'Overview',
    items: [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { label: 'Analytics', href: '/dashboard/analytics', icon: BarChart3 },
      { label: 'Risk Score', href: '/dashboard/risk-score', icon: ShieldCheck },
    ],
  },
  {
    title: 'Security',
    items: [
      { label: 'Incidents', href: '/dashboard/incidents', icon: AlertTriangle },
      { label: 'Agents', href: '/dashboard/agents', icon: Bot },
      { label: 'Detectors', href: '/dashboard/detectors', icon: Search },
      { label: 'Reviews', href: '/dashboard/reviews', icon: Eye },
      { label: 'Alerts', href: '/dashboard/alerts', icon: Bell },
      { label: 'Sandboxes', href: '/dashboard/sandboxes', icon: Box },
      { label: 'Model Registry', href: '/dashboard/model-registry', icon: Layers },
    ],
  },
  {
    title: 'Intelligence',
    items: [
      { label: 'Shadow AI', href: '/dashboard/shadow-ai', icon: Ghost },
      { label: 'Traces', href: '/dashboard/traces', icon: Route },
      { label: 'Conversations', href: '/dashboard/conversations', icon: MessageSquare },
      { label: 'Threat Intel', href: '/dashboard/threat-intel', icon: Shield },
      { label: 'Red Team', href: '/dashboard/red-team', icon: Target },
    ],
  },
  {
    title: 'Tools',
    items: [
      { label: 'Playground', href: '/dashboard/playground', icon: FlaskConical },
      { label: 'API Keys', href: '/dashboard/api-keys', icon: Key },
    ],
  },
  {
    title: 'Settings',
    items: [
      { label: 'Billing', href: '/dashboard/billing', icon: CreditCard },
      { label: 'Compliance', href: '/dashboard/compliance', icon: ClipboardCheck },
      { label: 'Settings', href: '/dashboard/settings', icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 flex h-screen w-64 flex-col border-r border-border bg-card" aria-label="Main navigation">
      <div className="flex h-14 items-center border-b border-border px-5">
        <Link href="/dashboard" className="flex items-center gap-2" aria-label="AgentGuard Dashboard">
          <Logo className="h-7 w-7" />
          <span className="text-sm font-semibold text-foreground">AgentGuard</span>
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-3" aria-label="Dashboard navigation">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="mb-4" role="group" aria-label={section.title}>
            <p className="mb-1 px-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground" aria-hidden="true">
              {section.title}
            </p>
            {section.items.map((item) => {
              const isActive =
                item.href === '/dashboard'
                  ? pathname === '/dashboard'
                  : pathname.startsWith(item.href);
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isActive ? 'page' : undefined}
                  className={clsx(
                    'flex items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                  )}
                >
                  <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
