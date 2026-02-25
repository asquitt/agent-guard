'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth, MfaRequiredError } from '@/hooks/useAuth';
import { ApiError } from '@/lib/api/client';
import Logo from '@/components/ui/Logo';

export default function LoginPage() {
  const { login, verifyMfaLogin } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // MFA state
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err) {
      if (err instanceof MfaRequiredError) {
        setMfaToken(err.mfaToken);
        setLoading(false);
        return;
      }
      if (err instanceof ApiError && err.status === 403) {
        setError('Your organization requires SSO. Redirecting...');
        setTimeout(() => router.push('/login/sso'), 1500);
        return;
      }
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleMfaSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!mfaToken) return;
    setError('');
    setLoading(true);

    try {
      await verifyMfaLogin(mfaToken, mfaCode);
      router.push('/dashboard');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Invalid code. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  // MFA verification step
  if (mfaToken) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <Logo className="mx-auto mb-4 h-10 w-10" />
            <h1 className="text-3xl font-bold text-foreground">Two-Factor Authentication</h1>
            <p className="mt-2 text-muted-foreground">
              Enter the 6-digit code from your authenticator app
            </p>
          </div>

          <form
            onSubmit={handleMfaSubmit}
            className="rounded-xl border border-border bg-card p-8"
          >
            {error && (
              <div role="alert" className="mb-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="mfa-code" className="mb-1 block text-sm font-medium text-foreground">
                Verification Code
              </label>
              <input
                id="mfa-code"
                type="text"
                required
                autoFocus
                autoComplete="one-time-code"
                inputMode="numeric"
                maxLength={8}
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-center text-lg tracking-widest text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="000000"
              />
              <p className="mt-2 text-xs text-muted-foreground">
                You can also use a backup code
              </p>
            </div>

            <button
              type="submit"
              disabled={loading || mfaCode.length < 6}
              className="mt-6 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Verify'}
            </button>

            <button
              type="button"
              onClick={() => { setMfaToken(null); setMfaCode(''); setError(''); }}
              className="mt-3 w-full text-sm text-muted-foreground hover:text-foreground"
            >
              Back to login
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <Logo className="mx-auto mb-4 h-10 w-10" />
          <h1 className="text-3xl font-bold text-foreground">AgentGuard</h1>
          <p className="mt-2 text-muted-foreground">Sign in to your account</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-border bg-card p-8"
        >
          {error && (
            <div id="login-error" role="alert" className="mb-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="mb-1 block text-sm font-medium text-foreground"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                aria-invalid={!!error}
                aria-describedby={error ? 'login-error' : undefined}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="you@company.com"
              />
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-foreground"
                >
                  Password
                </label>
                <Link
                  href="/forgot-password"
                  className="text-xs font-medium text-primary hover:text-primary/80"
                >
                  Forgot password?
                </Link>
              </div>
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                aria-invalid={!!error}
                aria-describedby={error ? 'login-error' : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link
              href="/register"
              className="font-medium text-primary hover:text-primary"
            >
              Create one
            </Link>
          </p>

          <div className="mt-4 border-t border-border pt-4 text-center">
            <Link
              href="/login/sso"
              className="text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              Sign in with SSO
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
