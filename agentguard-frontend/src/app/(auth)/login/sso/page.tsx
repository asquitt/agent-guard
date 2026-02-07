'use client';

import { useState } from 'react';
import Link from 'next/link';
import { getSSOInitiateUrl } from '@/lib/api/sso';

export default function SSOLoginPage() {
  const [orgSlug, setOrgSlug] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    const slug = orgSlug.trim().toLowerCase();
    if (!slug) {
      setError('Please enter your organization slug');
      return;
    }

    setLoading(true);
    // Redirect to backend SSO initiate endpoint
    window.location.href = getSSOInitiateUrl(slug);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">AgentGuard</h1>
          <p className="mt-2 text-gray-600">Sign in with SSO</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm"
        >
          {error && (
            <div className="mb-4 rounded-lg bg-danger-50 px-4 py-3 text-sm text-danger-600">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label
                htmlFor="orgSlug"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Organization slug
              </label>
              <input
                id="orgSlug"
                type="text"
                required
                value={orgSlug}
                onChange={(e) => setOrgSlug(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                placeholder="acme-corp"
              />
              <p className="mt-1 text-xs text-gray-500">
                Enter the slug your admin provided during setup
              </p>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? 'Redirecting...' : 'Continue with SSO'}
          </button>

          <p className="mt-4 text-center text-sm text-gray-600">
            <Link
              href="/login"
              className="font-medium text-primary-600 hover:text-primary-700"
            >
              Sign in with password instead
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
