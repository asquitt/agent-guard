'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import { updateProfileApi } from '@/lib/api';

export default function ProfilePage() {
  const { user, organization, fetchMe } = useAuth();
  const { success: toastSuccess, error: toastError } = useToast();
  const [name, setName] = useState(user?.name ?? '');
  const [saved, setSaved] = useState(false);

  const updateMutation = useMutation({
    mutationFn: (data: { full_name: string }) => updateProfileApi(data),
    onSuccess: async () => {
      await fetchMe();
      setSaved(true);
      toastSuccess('Profile updated');
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err: Error) => {
      toastError(err.message || 'Failed to update profile');
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    updateMutation.mutate({ full_name: name.trim() });
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Profile</h1>
        <p className="text-sm text-muted-foreground">
          Manage your account information
        </p>
      </div>

      {/* Avatar + Name */}
      <div className="mb-6 rounded-xl border border-border bg-card p-6">
        <div className="mb-6 flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/20 text-2xl font-bold text-primary">
            {user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
          </div>
          <div>
            <p className="text-lg font-semibold text-foreground">{user?.name}</p>
            <p className="text-sm text-muted-foreground">{user?.email}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="profile-full-name" className="mb-1 block text-xs font-medium text-foreground">
              Full Name
            </label>
            <input
              id="profile-full-name"
              value={name}
              onChange={(e) => { setName(e.target.value); setSaved(false); }}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
              required
              minLength={1}
              maxLength={255}
            />
          </div>
          <div>
            <label htmlFor="profile-email" className="mb-1 block text-xs font-medium text-foreground">
              Email
            </label>
            <input
              id="profile-email"
              value={user?.email ?? ''}
              disabled
              className="w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-muted-foreground"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Contact support to change your email address
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={updateMutation.isPending || name.trim() === user?.name}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
            {saved && (
              <span className="text-sm text-green-500">Saved</span>
            )}
            {updateMutation.isError && (
              <span className="text-sm text-red-500">Failed to save</span>
            )}
          </div>
        </form>
      </div>

      {/* Account Details (read-only) */}
      <div className="mb-6 rounded-xl border border-border bg-card p-6">
        <h2 className="mb-4 text-sm font-semibold text-foreground">Account Details</h2>
        <div className="space-y-3">
          <Row label="Role" value={user?.role ?? '—'} />
          <Row label="Organization" value={organization?.name ?? '—'} />
          <Row label="Plan" value={organization?.planTier ?? '—'} />
          <Row
            label="Member since"
            value={user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : '—'}
          />
        </div>
      </div>

      {/* Security */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="mb-4 text-sm font-semibold text-foreground">Security</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">Password</p>
              <p className="text-xs text-muted-foreground">
                Change your account password
              </p>
            </div>
            <a
              href="/dashboard/settings"
              className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
            >
              Change Password
            </a>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">Active Sessions</p>
              <p className="text-xs text-muted-foreground">
                Manage devices logged into your account
              </p>
            </div>
            <span className="text-xs text-muted-foreground">Coming soon</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium text-foreground">{value}</span>
    </div>
  );
}
