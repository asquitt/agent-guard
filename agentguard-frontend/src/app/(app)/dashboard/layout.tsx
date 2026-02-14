'use client';

import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { Breadcrumbs } from '@/components/ui/Breadcrumbs';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-primary focus:px-4 focus:py-2 focus:text-white">
          Skip to main content
        </a>
        <Sidebar />
        <Header />
        <CommandPalette />
        <main id="main-content" className="ml-64 pt-14" tabIndex={-1}>
          <div className="p-6">
            <Breadcrumbs />
            {children}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
