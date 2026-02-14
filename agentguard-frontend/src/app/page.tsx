import type { Metadata } from 'next';

import LandingNav from '@/components/landing/LandingNav';
import HeroSection from '@/components/landing/HeroSection';
import TrustBar from '@/components/landing/TrustBar';
import MetricsBar from '@/components/landing/MetricsBar';
import FeaturesGrid from '@/components/landing/FeaturesGrid';
import CodeSnippet from '@/components/landing/CodeSnippet';
import HowItWorks from '@/components/landing/HowItWorks';
import DashboardPreview from '@/components/landing/DashboardPreview';
import IntegrationsSection from '@/components/landing/IntegrationsSection';
import ComplianceSection from '@/components/landing/ComplianceSection';
import PricingSection from '@/components/landing/PricingSection';
import FaqSection from '@/components/landing/FaqSection';
import CtaSection from '@/components/landing/CtaSection';
import Footer from '@/components/landing/Footer';

export const metadata: Metadata = {
  title: 'AgentGuard - AI Agent Incident Response for Financial Services',
  description:
    'Real-time detection, compliance monitoring, and automated incident response for AI agents in regulated financial environments.',
  openGraph: {
    title: 'AgentGuard - AI Agent Incident Response for Financial Services',
    description:
      'Real-time detection, compliance monitoring, and automated incident response for AI agents in regulated financial environments.',
  },
};

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-background">
      <LandingNav />
      <HeroSection />
      <TrustBar />
      <MetricsBar />
      <FeaturesGrid />
      <CodeSnippet />
      <HowItWorks />
      <DashboardPreview />
      <IntegrationsSection />
      <ComplianceSection />
      <PricingSection />
      <FaqSection />
      <CtaSection />
      <Footer />
    </main>
  );
}
