import type { Metadata } from 'next';

import LandingNav from '@/components/landing/LandingNav';
import Footer from '@/components/landing/Footer';

export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-background">
      <LandingNav />
      <div className="pt-16">
        <aside
          aria-label="Archive status"
          className="border-b border-border bg-muted/40 px-6 py-4"
        >
          <p className="mx-auto max-w-5xl text-center text-sm leading-relaxed text-muted-foreground">
            <span className="font-semibold text-foreground">Archived reference.</span>{' '}
            AgentGuard is mothballed as a standalone product. These pages are
            preserved historical material, not an offer to register, purchase,
            deploy, or route provider traffic.
          </p>
        </aside>
        {children}
      </div>
      <Footer />
    </main>
  );
}
