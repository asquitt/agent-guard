import type { Metadata } from 'next';

import LandingNav from '@/components/landing/LandingNav';
import HeroSection from '@/components/landing/HeroSection';
import ArchiveDispositionSection from '@/components/landing/PricingSection';
import CtaSection from '@/components/landing/CtaSection';
import Footer from '@/components/landing/Footer';

export const metadata: Metadata = {
  title: 'AgentGuard - Archived Standalone Project',
  description:
    'AgentGuard is mothballed as a standalone product and preserved as a non-operational archive and reference.',
  robots: { index: false, follow: false },
  openGraph: {
    title: 'AgentGuard - Archived Standalone Project',
    description:
      'AgentGuard is mothballed as a standalone product and preserved as a non-operational archive and reference.',
  },
};

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-background">
      <LandingNav />
      <HeroSection />
      <ArchiveDispositionSection />
      <CtaSection />
      <Footer />
    </main>
  );
}
