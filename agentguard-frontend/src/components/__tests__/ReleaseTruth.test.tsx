import { render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import AboutPage, {
  metadata as aboutMetadata,
} from '@/app/(public)/about/page';
import BlogPage, { metadata as blogMetadata } from '@/app/(public)/blog/page';
import CareersPage, {
  metadata as careersMetadata,
} from '@/app/(public)/careers/page';
import ChangelogPage, {
  metadata as changelogMetadata,
} from '@/app/(public)/changelog/page';
import DocsPage, { metadata as docsMetadata } from '@/app/(public)/docs/page';
import PublicLayout, {
  metadata as publicMetadata,
} from '@/app/(public)/layout';
import PricingPage, {
  metadata as pricingMetadata,
} from '@/app/(public)/pricing/page';
import PrivacyPage, {
  metadata as privacyMetadata,
} from '@/app/(public)/privacy/page';
import SecurityPage, {
  metadata as securityMetadata,
} from '@/app/(public)/security/page';
import TermsPage, {
  metadata as termsMetadata,
} from '@/app/(public)/terms/page';
import LandingPage, { metadata as landingMetadata } from '@/app/page';
import StatusPage from '@/app/status/page';
import { siteMetadata as rootMetadata } from '@/lib/site-metadata';

const FORBIDDEN_PUBLIC_CLAIMS = [
  'Meridian Capital',
  'Atlas Financial',
  'Pinnacle Bank',
  'Vertex Securities',
  'Horizon Trust',
  'Trusted by teams securing AI agents at leading financial institutions',
  '<2ms',
  '99.9%',
  '99.99%',
  '50M+',
  '1.2M',
  '99.7%',
  '2.1ms',
  'Full Protection',
  'sub-millisecond overhead',
  'Deploy in minutes',
  'Every model. Full visibility',
  'Automated incident response',
  '$499',
  '$1,999',
  '14-day free trial',
  'Unlimited LLM requests',
  'SLA guarantees',
  'SOC 2-compliant',
  '24/7 security monitoring',
  'Regular penetration testing by independent third-party firms',
  'audit is currently in progress',
  'Data never leaves your infrastructure',
  'Get Started Free',
  'proxy.agentguard.dev',
  'api.agentguard.app',
  'operate safely in production',
  'covered from day one',
  'One line of code to integrate',
  'monitor every AI agent interaction',
  'respond automatically',
  'All requests are analyzed in real-time',
  'ships with 6 detection categories enabled by default',
  'Our platform is hosted in the United States',
  'AES-256 and TLS 1.3',
  'custom DPAs are available upon request',
  'Subscription fees are billed monthly or annually',
  'AgentGuard targets 99.9% uptime',
  'PII leak prevention with automatic blocking',
  'Senior Backend Engineer',
  'Meaningful Equity',
  'Comprehensive health, dental, and vision coverage',
  'https://agentguard.dev',
  'sales@agentguard.dev',
  'privacy@agentguard.dev',
  'legal@agentguard.dev',
  'careers@agentguard.dev',
  'Self-service registration',
  'public registration flow',
  'Create Evaluation Workspace',
  'Create evaluation workspace',
  'Create a controlled evaluation workspace',
  'Pre-release evaluation',
  'Limited pilot',
  'Coming soon',
];

const PUBLIC_ROUTES = [
  { path: '/', element: <LandingPage /> },
  { path: '/about', element: <PublicLayout><AboutPage /></PublicLayout> },
  { path: '/blog', element: <PublicLayout><BlogPage /></PublicLayout> },
  { path: '/careers', element: <PublicLayout><CareersPage /></PublicLayout> },
  { path: '/changelog', element: <PublicLayout><ChangelogPage /></PublicLayout> },
  { path: '/docs', element: <PublicLayout><DocsPage /></PublicLayout> },
  { path: '/pricing', element: <PublicLayout><PricingPage /></PublicLayout> },
  { path: '/privacy', element: <PublicLayout><PrivacyPage /></PublicLayout> },
  { path: '/security', element: <PublicLayout><SecurityPage /></PublicLayout> },
  { path: '/terms', element: <PublicLayout><TermsPage /></PublicLayout> },
  { path: '/status', element: <StatusPage /> },
] as const;

const PUBLIC_METADATA = [
  rootMetadata,
  landingMetadata,
  publicMetadata,
  aboutMetadata,
  blogMetadata,
  careersMetadata,
  changelogMetadata,
  docsMetadata,
  pricingMetadata,
  privacyMetadata,
  securityMetadata,
  termsMetadata,
];

function collectPublicCopy() {
  const copy: string[] = [];
  for (const route of PUBLIC_ROUTES) {
    const { container, unmount } = render(route.element);
    copy.push(container.textContent ?? '');
    unmount();
  }
  copy.push(...PUBLIC_METADATA.map((metadata) => JSON.stringify(metadata)));
  return copy.join(' ');
}

describe('public archive truth', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Archive health unavailable'));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not render unsupported customer, performance, plan, or active-product claims', () => {
    const publicCopy = collectPublicCopy();

    for (const claim of FORBIDDEN_PUBLIC_CLAIMS) {
      expect(publicCopy).not.toContain(claim);
    }
    expect(publicCopy.toLowerCase()).not.toContain('self-service');
  });

  it('labels every public route as archived or mothballed', () => {
    for (const route of PUBLIC_ROUTES) {
      const { container, unmount } = render(route.element);
      expect(container.textContent?.toLowerCase()).toMatch(/archived|mothballed/);
      unmount();
    }

    const publicCopy = collectPublicCopy();
    expect(publicCopy).toContain('AgentGuard is mothballed as a standalone product');
    expect(publicCopy).toContain(
      'Customer acquisition, registration, deployments, and provider/runtime use are not authorized.',
    );
    expect(publicCopy).toContain('No prices, plans, trials, pilots, or workspaces are offered.');
  });

  it('keeps root, landing, and public-segment metadata non-indexable', () => {
    expect(rootMetadata.robots).toMatchObject({ index: false, follow: false });
    expect(landingMetadata.robots).toMatchObject({ index: false, follow: false });
    expect(publicMetadata.robots).toMatchObject({ index: false, follow: false });
    expect(JSON.stringify(rootMetadata)).toContain('mothballed');
    expect(JSON.stringify(landingMetadata)).toContain('Archived Standalone Project');
  });

  it('offers no registration, pricing, or provider/runtime action on public routes', () => {
    for (const route of PUBLIC_ROUTES) {
      const { container, unmount } = render(route.element);
      const hrefs = Array.from(container.querySelectorAll('a[href]')).map((link) =>
        link.getAttribute('href'),
      );

      expect(hrefs).not.toContain('/register');
      expect(hrefs).not.toContain('/pricing');
      expect(hrefs).not.toContain('/#pricing');
      expect(container.querySelector('form')).toBeNull();
      expect(container.textContent).not.toContain('AGENTGUARD_API_KEY');
      expect(container.textContent).not.toContain('X-AgentGuard-Endpoint-Id');
      expect(container.textContent).not.toContain('from openai import OpenAI');
      unmount();
    }
  });

  it('keeps every public link on an existing route, archive anchor, or approved external destination', () => {
    const knownRoutes = new Set([
      '/',
      '/about',
      '/blog',
      '/careers',
      '/changelog',
      '/docs',
      '/login',
      '/privacy',
      '/security',
      '/status',
      '/terms',
    ]);
    const knownAnchors = new Map([
      ['/', new Set(['archive'])],
      ['/security', new Set(['assurance'])],
    ]);
    const approvedExternalUrls = new Set([
      'https://github.com/asquitt/agent-guard/security/advisories/new',
    ]);

    for (const currentRoute of PUBLIC_ROUTES) {
      const { container, unmount } = render(currentRoute.element);
      for (const link of Array.from(container.querySelectorAll('a[href]'))) {
        const href = link.getAttribute('href');
        expect(href).not.toBeNull();

        if (!href) continue;
        if (href.startsWith('https://')) {
          expect(approvedExternalUrls).toContain(href);
          continue;
        }
        expect(href.startsWith('mailto:')).toBe(false);

        if (href.startsWith('#')) {
          expect(container.querySelector(href)).not.toBeNull();
          continue;
        }

        const [route, fragment] = href.split('#');
        expect(knownRoutes).toContain(route);
        if (fragment) {
          expect(knownAnchors.get(route)?.has(fragment)).toBe(true);
        }
      }
      unmount();
    }
  });
});
