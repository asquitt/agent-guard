import type { Metadata } from 'next';

export function createSiteMetadata(configuredSiteUrl: string | undefined): Metadata {
  return {
    title: {
      default: 'AgentGuard - Archived Standalone Project',
      template: '%s | AgentGuard',
    },
    description:
      'AgentGuard is mothballed as a standalone product. This non-operational site is preserved for archive and reference use.',
    ...(configuredSiteUrl ? { metadataBase: new URL(configuredSiteUrl) } : {}),
    openGraph: {
      type: 'website',
      siteName: 'AgentGuard',
      title: 'AgentGuard - Archived Standalone Project',
      description:
        'AgentGuard is mothballed as a standalone product and preserved as a non-operational reference.',
      ...(configuredSiteUrl ? { url: configuredSiteUrl } : {}),
    },
    twitter: {
      card: 'summary_large_image',
      title: 'AgentGuard - Archived Standalone Project',
      description:
        'AgentGuard is mothballed as a standalone product and preserved as a non-operational reference.',
    },
    robots: {
      index: false,
      follow: false,
    },
  };
}

export const siteMetadata = createSiteMetadata(process.env.NEXT_PUBLIC_SITE_URL);
