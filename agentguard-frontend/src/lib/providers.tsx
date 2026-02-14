'use client';

import {
  QueryClient,
  QueryClientProvider,
  useQueryClient,
} from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { ThemeProvider } from 'next-themes';
import { AuthProvider } from '@/hooks/useAuth';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { WebSocketEvent } from '@/hooks/useWebSocket';

function WebSocketManager({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const { lastEvent } = useWebSocket();

  useEffect(() => {
    if (!lastEvent || lastEvent.type === 'connected') return;

    switch (lastEvent.type) {
      case 'incident.new':
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] });
        queryClient.invalidateQueries({ queryKey: ['incidents'] });
        break;
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
  }, [lastEvent, queryClient]);

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
      }),
  );

  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <WebSocketManager>{children}</WebSocketManager>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
