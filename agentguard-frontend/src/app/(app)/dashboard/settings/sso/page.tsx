'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import {
  createSSOConfig,
  deleteSSOConfig,
  getSSOConfig,
  testSSOConnection,
  toggleSSOEnforcement,
  updateSSOConfig,
} from '@/lib/api/sso';
import type { SSOConfig, SSOConfigCreate } from '@/types/sso';
import { ApiError } from '@/lib/api/client';

export default function SSOSettingsPage() {
  const { user, organization } = useAuth();
  const [config, setConfig] = useState<SSOConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'saml' | 'oidc'>('saml');

  // Form state
  const [samlEntityId, setSamlEntityId] = useState('');
  const [samlSsoUrl, setSamlSsoUrl] = useState('');
  const [samlX509Cert, setSamlX509Cert] = useState('');
  const [samlMetadataXml, setSamlMetadataXml] = useState('');
  const [oidcIssuer, setOidcIssuer] = useState('');
  const [oidcClientId, setOidcClientId] = useState('');
  const [oidcClientSecret, setOidcClientSecret] = useState('');
  const [oidcDiscoveryUrl, setOidcDiscoveryUrl] = useState('');
  const [enforced, setEnforced] = useState(false);

  const isAdmin = user?.role === 'admin';

  useEffect(() => {
    loadConfig();
    if (organization?.settings) {
      const settings = organization.settings as Record<string, unknown>;
      setEnforced(!!settings.sso_enforced);
    }
  }, [organization]);

  async function loadConfig() {
    try {
      const c = await getSSOConfig();
      setConfig(c);
      setTab(c.providerType);
      setSamlEntityId(c.samlEntityId ?? '');
      setSamlSsoUrl(c.samlSsoUrl ?? '');
      setSamlX509Cert(c.samlX509Cert ?? '');
      setOidcIssuer(c.oidcIssuer ?? '');
      setOidcClientId(c.oidcClientId ?? '');
      setOidcDiscoveryUrl(c.oidcDiscoveryUrl ?? '');
    } catch {
      // No config yet — that's fine
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError('');
    setMessage('');

    try {
      if (config) {
        const updated = await updateSSOConfig(config.id, {
          samlEntityId: tab === 'saml' ? samlEntityId : undefined,
          samlSsoUrl: tab === 'saml' ? samlSsoUrl : undefined,
          samlX509Cert: tab === 'saml' ? samlX509Cert : undefined,
          samlMetadataXml: tab === 'saml' ? samlMetadataXml : undefined,
          oidcIssuer: tab === 'oidc' ? oidcIssuer : undefined,
          oidcClientId: tab === 'oidc' ? oidcClientId : undefined,
          oidcClientSecret: tab === 'oidc' ? (oidcClientSecret || undefined) : undefined,
          oidcDiscoveryUrl: tab === 'oidc' ? oidcDiscoveryUrl : undefined,
        });
        setConfig(updated);
        setMessage('SSO configuration updated');
      } else {
        const data: SSOConfigCreate = {
          providerType: tab,
          samlEntityId: tab === 'saml' ? samlEntityId : undefined,
          samlSsoUrl: tab === 'saml' ? samlSsoUrl : undefined,
          samlX509Cert: tab === 'saml' ? samlX509Cert : undefined,
          samlMetadataXml: tab === 'saml' ? samlMetadataXml : undefined,
          oidcIssuer: tab === 'oidc' ? oidcIssuer : undefined,
          oidcClientId: tab === 'oidc' ? oidcClientId : undefined,
          oidcClientSecret: tab === 'oidc' ? oidcClientSecret : undefined,
          oidcDiscoveryUrl: tab === 'oidc' ? oidcDiscoveryUrl : undefined,
        };
        const created = await createSSOConfig(data);
        setConfig(created);
        setMessage('SSO configuration created');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to save SSO configuration');
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setError('');
    setMessage('');
    try {
      const result = await testSSOConnection();
      if (result.success) {
        setMessage(result.message);
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Test failed');
    } finally {
      setTesting(false);
    }
  }

  async function handleDelete() {
    if (!config || !confirm('Remove SSO configuration? Users will need to use password login.')) return;
    try {
      await deleteSSOConfig(config.id);
      setConfig(null);
      setSamlEntityId('');
      setSamlSsoUrl('');
      setSamlX509Cert('');
      setOidcIssuer('');
      setOidcClientId('');
      setOidcClientSecret('');
      setOidcDiscoveryUrl('');
      setMessage('SSO configuration removed');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to delete');
    }
  }

  async function handleEnforcementToggle() {
    const newValue = !enforced;
    try {
      await toggleSSOEnforcement(newValue);
      setEnforced(newValue);
      setMessage(newValue ? 'SSO enforcement enabled' : 'SSO enforcement disabled');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to toggle enforcement');
    }
  }

  if (!isAdmin) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center">
        <p className="text-sm text-muted-foreground">Admin access required to manage SSO settings.</p>
        <Link href="/dashboard/settings" className="mt-4 inline-block text-sm text-primary hover:text-primary">
          Back to Settings
        </Link>
      </div>
    );
  }

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading SSO configuration...</div>;
  }

  return (
    <div>
      <div className="mb-6">
        <Link href="/dashboard/settings" className="text-sm text-muted-foreground hover:text-foreground">
          &larr; Settings
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-foreground">Single Sign-On</h1>
        <p className="text-sm text-muted-foreground">
          Configure SAML 2.0 or OIDC for enterprise authentication
        </p>
      </div>

      {message && (
        <div className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">{message}</div>
      )}
      {error && (
        <div className="mb-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Provider tabs */}
      <div className="mb-6 flex gap-2">
        <button
          onClick={() => setTab('saml')}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            tab === 'saml' ? 'bg-primary text-white' : 'bg-muted text-foreground hover:bg-muted'
          }`}
        >
          SAML 2.0
        </button>
        <button
          onClick={() => setTab('oidc')}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            tab === 'oidc' ? 'bg-primary text-white' : 'bg-muted text-foreground hover:bg-muted'
          }`}
        >
          OpenID Connect
        </button>
      </div>

      {/* SAML config */}
      {tab === 'saml' && (
        <div className="space-y-4 rounded-xl border border-border bg-card p-6">
          <h2 className="text-lg font-semibold text-foreground">SAML 2.0 Configuration</h2>
          <FormField label="IdP Entity ID" value={samlEntityId} onChange={setSamlEntityId} placeholder="https://idp.example.com/metadata" />
          <FormField label="IdP SSO URL" value={samlSsoUrl} onChange={setSamlSsoUrl} placeholder="https://idp.example.com/sso/saml" />
          <FormField label="IdP X.509 Certificate" value={samlX509Cert} onChange={setSamlX509Cert} placeholder="Paste PEM certificate..." multiline />
          <FormField label="IdP Metadata XML (optional)" value={samlMetadataXml} onChange={setSamlMetadataXml} placeholder="Paste metadata XML to auto-fill above fields..." multiline />
          <div className="rounded-lg bg-muted/50 p-3">
            <p className="text-xs font-medium text-muted-foreground">SP Metadata URL</p>
            <code className="text-xs text-muted-foreground">
              {`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/auth/sso/saml/metadata/${organization?.slug ?? 'your-org'}`}
            </code>
          </div>
        </div>
      )}

      {/* OIDC config */}
      {tab === 'oidc' && (
        <div className="space-y-4 rounded-xl border border-border bg-card p-6">
          <h2 className="text-lg font-semibold text-foreground">OpenID Connect Configuration</h2>
          <FormField label="Issuer URL" value={oidcIssuer} onChange={setOidcIssuer} placeholder="https://accounts.google.com" />
          <FormField label="Client ID" value={oidcClientId} onChange={setOidcClientId} placeholder="your-client-id" />
          <FormField label="Client Secret" value={oidcClientSecret} onChange={setOidcClientSecret} placeholder={config?.oidcClientSecretSet ? '(unchanged — enter new value to update)' : 'your-client-secret'} type="password" />
          <FormField label="Discovery URL (optional)" value={oidcDiscoveryUrl} onChange={setOidcDiscoveryUrl} placeholder="Auto-derived from issuer if blank" />
        </div>
      )}

      {/* Actions */}
      <div className="mt-6 flex flex-wrap gap-3">
        <button onClick={handleSave} disabled={saving} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/80 disabled:opacity-50">
          {saving ? 'Saving...' : config ? 'Update Configuration' : 'Save Configuration'}
        </button>
        {config && (
          <>
            <button onClick={handleTest} disabled={testing} className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50 disabled:opacity-50">
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            <button onClick={handleDelete} className="rounded-lg border border-danger-300 bg-card px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-500/10">
              Remove SSO
            </button>
          </>
        )}
      </div>

      {/* SSO Enforcement */}
      {config && (
        <div className="mt-8 rounded-xl border border-border bg-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Enforce SSO</h3>
              <p className="mt-1 text-xs text-muted-foreground">
                When enabled, password login is disabled for all users in this organization.
              </p>
            </div>
            <button
              onClick={handleEnforcementToggle}
              className={`relative h-6 w-11 rounded-full transition-colors ${
                enforced ? 'bg-primary' : 'bg-muted'
              }`}
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-card shadow transition-transform ${
                  enforced ? 'left-[22px]' : 'left-0.5'
                }`}
              />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function FormField({
  label,
  value,
  onChange,
  placeholder = '',
  type = 'text',
  multiline = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  multiline?: boolean;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-foreground">{label}</label>
      {multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={4}
          className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
      ) : (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
      )}
    </div>
  );
}
