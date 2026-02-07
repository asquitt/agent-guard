'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function SSOCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    const refresh = searchParams.get('refresh');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      setError(decodeURIComponent(errorParam));
      return;
    }

    if (token && refresh) {
      // Store tokens and redirect to dashboard
      localStorage.setItem('accessToken', token);
      localStorage.setItem('refreshToken', refresh);
      router.push('/dashboard');
    } else {
      setError('Missing authentication tokens');
    }
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-md text-center">
          <h1 className="text-2xl font-bold text-gray-900">SSO Login Failed</h1>
          <p className="mt-4 text-sm text-danger-600">{error}</p>
          <a
            href="/login"
            className="mt-6 inline-block rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
          >
            Back to Login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        <p className="mt-4 text-sm text-gray-500">Completing sign in...</p>
      </div>
    </div>
  );
}

export default function SSOCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-gray-50">
          <div className="text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
            <p className="mt-4 text-sm text-gray-500">Loading...</p>
          </div>
        </div>
      }
    >
      <SSOCallbackContent />
    </Suspense>
  );
}
