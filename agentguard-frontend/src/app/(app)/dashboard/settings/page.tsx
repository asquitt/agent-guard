'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';

export default function SettingsPage() {
  const { user, organization } = useAuth();

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your organization and account
        </p>
      </div>

      {/* Organization */}
      <div className="mb-6 rounded-xl border border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          Organization
        </h2>
        <div className="space-y-3">
          <SettingsRow label="Name" value={organization?.name ?? '—'} />
          <SettingsRow label="Slug" value={organization?.slug ?? '—'} />
          <SettingsRow label="Plan" value={organization?.planTier ?? '—'} />
          <SettingsRow
            label="Created"
            value={
              organization?.createdAt
                ? new Date(organization.createdAt).toLocaleDateString()
                : '—'
            }
          />
        </div>
      </div>

      {/* Account */}
      <div className="mb-6 rounded-xl border border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">Account</h2>
        <div className="space-y-3">
          <SettingsRow label="Name" value={user?.name ?? '—'} />
          <SettingsRow label="Email" value={user?.email ?? '—'} />
          <SettingsRow label="Role" value={user?.role ?? '—'} />
          <SettingsRow
            label="Member since"
            value={
              user?.createdAt
                ? new Date(user.createdAt).toLocaleDateString()
                : '—'
            }
          />
        </div>
      </div>

      {/* Placeholder sections */}
      <div className="space-y-4">
        <PlaceholderSection
          title="Team Management"
          description="Invite members, manage roles, and remove users"
        />
        <Link
          href="/dashboard/settings/sso"
          className="block rounded-xl border border-border bg-card p-6 transition-colors hover:bg-muted/50"
        >
          <h3 className="text-sm font-semibold text-foreground">Single Sign-On</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Configure SAML 2.0 or OIDC for enterprise authentication
          </p>
          <p className="mt-2 text-xs font-medium text-primary">
            Configure SSO &rarr;
          </p>
        </Link>
        <Link
          href="/dashboard/settings/ip-allowlist"
          className="block rounded-xl border border-border bg-card p-6 transition-colors hover:bg-muted/50"
        >
          <h3 className="text-sm font-semibold text-foreground">IP Allowlisting</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Restrict proxy access to specific IP addresses or CIDR ranges
          </p>
          <p className="mt-2 text-xs font-medium text-primary">
            Configure IPs &rarr;
          </p>
        </Link>
        <Link
          href="/dashboard/settings/data-residency"
          className="block rounded-xl border border-border bg-card p-6 transition-colors hover:bg-muted/50"
        >
          <h3 className="text-sm font-semibold text-foreground">Data Residency & Sovereignty</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Configure data regions, provider restrictions, and encryption for regulatory compliance
          </p>
          <p className="mt-2 text-xs font-medium text-primary">
            Configure Residency &rarr;
          </p>
        </Link>
        <Link
          href="/dashboard/settings/retention"
          className="block rounded-xl border border-border bg-card p-6 transition-colors hover:bg-muted/50"
        >
          <h3 className="text-sm font-semibold text-foreground">Data Retention</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Configure data archival policies and view archived data
          </p>
          <p className="mt-2 text-xs font-medium text-primary">
            Configure Retention &rarr;
          </p>
        </Link>
        <Link
          href="/dashboard/billing"
          className="block rounded-xl border border-border bg-card p-6 transition-colors hover:bg-muted/50"
        >
          <h3 className="text-sm font-semibold text-foreground">Billing</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Manage subscription, view usage, update payment method
          </p>
          <p className="mt-2 text-xs font-medium text-primary">
            Go to Billing &rarr;
          </p>
        </Link>
      </div>
    </div>
  );
}

function SettingsRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium text-foreground">{value}</span>
    </div>
  );
}

function PlaceholderSection({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-muted/50 p-6">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      <p className="mt-2 text-xs text-muted-foreground/60">Coming soon</p>
    </div>
  );
}
