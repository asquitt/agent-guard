'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';

interface NavItem {
  label: string;
  href: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: '📊' },
  { label: 'Incidents', href: '/dashboard/incidents', icon: '🚨' },
  { label: 'Agents', href: '/dashboard/agents', icon: '🤖' },
  { label: 'Detectors', href: '/dashboard/detectors', icon: '🔍' },
  { label: 'Alerts', href: '/dashboard/alerts', icon: '🔔' },
  { label: 'Traces', href: '/dashboard/traces', icon: '🔗' },
  { label: 'Playground', href: '/dashboard/playground', icon: '🧪' },
  { label: 'API Keys', href: '/dashboard/api-keys', icon: '🔑' },
  { label: 'Billing', href: '/dashboard/billing', icon: '💳' },
  { label: 'Compliance', href: '/dashboard/compliance', icon: '📋' },
  { label: 'Settings', href: '/dashboard/settings', icon: '⚙️' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 flex h-screen w-64 flex-col border-r border-gray-200 bg-white">
      <div className="flex h-16 items-center border-b border-gray-200 px-6">
        <Link href="/dashboard" className="flex items-center gap-2">
          <span className="text-xl font-bold text-primary-600">AgentGuard</span>
        </Link>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === '/dashboard'
              ? pathname === '/dashboard'
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900',
              )}
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
