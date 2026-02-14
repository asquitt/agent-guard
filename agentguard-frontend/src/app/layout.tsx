import type { Metadata } from 'next';
import { GeistSans } from 'geist/font/sans';
import { GeistMono } from 'geist/font/mono';
import './globals.css';
import { Providers } from '@/lib/providers';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://agentguard.dev';

export const metadata: Metadata = {
  title: {
    default: 'AgentGuard - AI Agent Security Platform',
    template: '%s | AgentGuard',
  },
  description: 'Real-time detection and response for AI agent threats in financial services',
  metadataBase: new URL(SITE_URL),
  openGraph: {
    type: 'website',
    siteName: 'AgentGuard',
    title: 'AgentGuard - AI Agent Security Platform',
    description:
      'Real-time detection, compliance monitoring, and automated incident response for AI agents in regulated financial environments.',
    url: SITE_URL,
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AgentGuard - AI Agent Security Platform',
    description:
      'Real-time detection and response for AI agent threats in financial services.',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
