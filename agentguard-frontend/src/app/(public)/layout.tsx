import LandingNav from '@/components/landing/LandingNav';
import Footer from '@/components/landing/Footer';

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-background">
      <LandingNav />
      <div className="pt-16">{children}</div>
      <Footer />
    </main>
  );
}
