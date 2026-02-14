'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';

const LABEL_MAP: Record<string, string> = {
  dashboard: 'Dashboard',
  incidents: 'Incidents',
  agents: 'Agents',
  detectors: 'Detectors',
  reviews: 'Reviews',
  alerts: 'Alerts',
  sandboxes: 'Sandboxes',
  'model-registry': 'Model Registry',
  'shadow-ai': 'Shadow AI',
  traces: 'Traces',
  conversations: 'Conversations',
  'threat-intel': 'Threat Intel',
  'red-team': 'Red Team',
  playground: 'Playground',
  'api-keys': 'API Keys',
  billing: 'Billing',
  compliance: 'Compliance',
  settings: 'Settings',
  analytics: 'Analytics',
  'risk-score': 'Risk Score',
  profile: 'Profile',
  notifications: 'Notifications',
  team: 'Team',
  sso: 'SSO',
  'ip-allowlist': 'IP Allowlist',
  'data-residency': 'Data Residency',
  siem: 'SIEM',
  retention: 'Data Retention',
};

export function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  // Only show breadcrumbs when we're at least 2 levels deep (/dashboard/X)
  if (segments.length <= 1) return null;

  const crumbs: { label: string; href: string }[] = [];
  let path = '';

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    path += `/${seg}`;

    // Skip UUID-like segments (detail pages) — show as "Details"
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-/.test(seg);
    const label = isUuid ? 'Details' : (LABEL_MAP[seg] ?? seg);

    crumbs.push({ label, href: path });
  }

  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-1 text-xs text-muted-foreground">
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1;
        return (
          <span key={crumb.href} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="h-3 w-3" />}
            {isLast ? (
              <span className="font-medium text-foreground">{crumb.label}</span>
            ) : (
              <Link href={crumb.href} className="hover:text-foreground transition-colors">
                {crumb.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
