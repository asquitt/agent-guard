'use client';

import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { KeyboardShortcuts } from '@/components/ui/KeyboardShortcuts';
import { Breadcrumbs } from '@/components/ui/Breadcrumbs';
import { NavigationProgress } from '@/components/ui/NavigationProgress';
import { SidebarProvider } from '@/hooks/useSidebar';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <SidebarProvider>
        <div className="min-h-screen bg-background">
          <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-primary focus:px-4 focus:py-2 focus:text-white">
            Skip to main content
          </a>
          <NavigationProgress />
          <Sidebar />
          <Header />
          <CommandPalette />
          <KeyboardShortcuts />
          <main id="main-content" className="pt-14 md:ml-64" tabIndex={-1}>
            <div className="animate-fade-in-up p-4 md:p-6">
              <Breadcrumbs />
              {children}
            </div>
          </main>
        </div>
      </SidebarProvider>
    </ProtectedRoute>
  );
}
