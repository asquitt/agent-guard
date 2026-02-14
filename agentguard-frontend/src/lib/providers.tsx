'use client';

import {
  MutationCache,
  QueryClient,
  QueryClientProvider,
  useQueryClient,
} from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { ThemeProvider } from 'next-themes';
import { AuthProvider } from '@/hooks/useAuth';
import { ToastProvider } from '@/hooks/useToast';
import { useWebSocket } from '@/hooks/useWebSocket';
import { pushWsEvent } from '@/hooks/useActivityFeed';
import { useToast } from '@/hooks/useToast';

const HIGH_SEVERITY = new Set(['critical', 'high']);

function WebSocketManager({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const { lastEvent } = useWebSocket();
  const toast = useToast();

  useEffect(() => {
    if (!lastEvent || lastEvent.type === 'connected') return;

    // Feed the activity store
    pushWsEvent(lastEvent);

    switch (lastEvent.type) {
      case 'incident.new': {
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] });
        queryClient.invalidateQueries({ queryKey: ['incidents'] });
        const severity = (lastEvent.data?.severity as string) ?? '';
        if (HIGH_SEVERITY.has(severity)) {
          const title = (lastEvent.data?.title as string) ?? 'New incident';
          toast.error(`🚨 ${severity.toUpperCase()}: ${title}`);
        }
        break;
      }
      case 'incident.updated':
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] });
        queryClient.invalidateQueries({ queryKey: ['incidents'] });
        break;
      case 'alert.sent':
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] });
        break;
      case 'billing.updated':
        queryClient.invalidateQueries({ queryKey: ['billing'] });
        break;
    }
  }, [lastEvent, queryClient, toast]);

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
          },
        },
        mutationCache: new MutationCache({
          onError: (error, _variables, _context, mutation) => {
            // Only show global toast if the mutation has no local onError handler.
            // This prevents duplicate toasts for mutations that handle errors themselves.
            if (mutation.options.onError) return;
            if (typeof window !== 'undefined') {
              window.dispatchEvent(
                new CustomEvent('api:mutation-error', {
                  detail: { message: error.message || 'Something went wrong' },
                }),
              );
            }
          },
        }),
      }),
  );

  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ToastProvider>
            <WebSocketManager>{children}</WebSocketManager>
          </ToastProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
