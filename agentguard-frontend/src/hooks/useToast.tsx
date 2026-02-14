'use client';

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Toast } from '@/components/ui/Toast';

type ToastSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

interface ToastItem {
  id: string;
  message: string;
  severity: ToastSeverity;
}

interface ToastContextValue {
  toast: (message: string, severity?: ToastSeverity) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
  success: () => {},
  error: () => {},
  warning: () => {},
});

let toastCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, severity: ToastSeverity = 'info') => {
    const id = `toast-${++toastCounter}`;
    setToasts((prev) => [...prev.slice(-4), { id, message, severity }]);
  }, []);

  const success = useCallback((message: string) => addToast(message, 'low'), [addToast]);
  const error = useCallback((message: string) => addToast(message, 'critical'), [addToast]);
  const warning = useCallback((message: string) => addToast(message, 'medium'), [addToast]);

  // Listen for rate-limit events from the API client
  useEffect(() => {
    function handleRateLimit(e: Event) {
      const ms = (e as CustomEvent).detail?.retryAfter ?? 2000;
      addToast(`Rate limited — retrying in ${Math.round(ms / 1000)}s`, 'medium');
    }
    window.addEventListener('api:rate-limited', handleRateLimit);
    return () => window.removeEventListener('api:rate-limited', handleRateLimit);
  }, [addToast]);

  // Listen for global mutation errors from TanStack Query MutationCache
  useEffect(() => {
    function handleMutationError(e: Event) {
      const msg = (e as CustomEvent).detail?.message ?? 'Something went wrong';
      addToast(msg, 'critical');
    }
    window.addEventListener('api:mutation-error', handleMutationError);
    return () => window.removeEventListener('api:mutation-error', handleMutationError);
  }, [addToast]);

  return (
    <ToastContext.Provider value={{ toast: addToast, success, error, warning }}>
      {children}
      {toasts.length > 0 && (
        <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
          {toasts.map((t) => (
            <Toast
              key={t.id}
              message={t.message}
              severity={t.severity}
              onDismiss={() => dismiss(t.id)}
            />
          ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
