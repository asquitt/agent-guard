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
    <div className="flex min-h-screen items-center justify-center bg-muted/50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground">AgentGuard</h1>
          <p className="mt-2 text-muted-foreground">Sign in with SSO</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-border bg-card p-8 shadow-sm shadow-black/10"
        >
          {error && (
            <div className="mb-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label
                htmlFor="orgSlug"
                className="mb-1 block text-sm font-medium text-foreground"
              >
                Organization slug
              </label>
              <input
                id="orgSlug"
                type="text"
                required
                value={orgSlug}
                onChange={(e) => setOrgSlug(e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="acme-corp"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Enter the slug your admin provided during setup
              </p>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary/80 disabled:opacity-50"
          >
            {loading ? 'Redirecting...' : 'Continue with SSO'}
          </button>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            <Link
              href="/login"
              className="font-medium text-primary hover:text-primary"
            >
              Sign in with password instead
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
