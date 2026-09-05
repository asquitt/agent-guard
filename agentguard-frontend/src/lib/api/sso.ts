/** SSO API client. */

import { apiFetch } from './client';
import { apiUrl } from './url';
import type { SSOCheckResult, SSOConfig, SSOConfigCreate, SSOConfigUpdate, SSOTestResult } from '@/types/sso';

// ─── Config Management (Admin) ──────────────────────────────────────────────

export async function getSSOConfig(): Promise<SSOConfig> {
  return apiFetch<SSOConfig>('/auth/sso/config');
}

export async function createSSOConfig(data: SSOConfigCreate): Promise<SSOConfig> {
  return apiFetch<SSOConfig>('/auth/sso/config', {
    method: 'POST',
    body: JSON.stringify({
      provider_type: data.providerType,
      saml_entity_id: data.samlEntityId,
      saml_sso_url: data.samlSsoUrl,
      saml_x509_cert: data.samlX509Cert,
      saml_metadata_xml: data.samlMetadataXml,
      oidc_issuer: data.oidcIssuer,
      oidc_client_id: data.oidcClientId,
      oidc_client_secret: data.oidcClientSecret,
      oidc_discovery_url: data.oidcDiscoveryUrl,
    }),
  });
}

export async function updateSSOConfig(configId: string, data: SSOConfigUpdate): Promise<SSOConfig> {
  return apiFetch<SSOConfig>(`/auth/sso/config/${configId}`, {
    method: 'PUT',
    body: JSON.stringify({
      enabled: data.enabled,
      saml_entity_id: data.samlEntityId,
      saml_sso_url: data.samlSsoUrl,
      saml_x509_cert: data.samlX509Cert,
      saml_metadata_xml: data.samlMetadataXml,
      oidc_issuer: data.oidcIssuer,
      oidc_client_id: data.oidcClientId,
      oidc_client_secret: data.oidcClientSecret,
      oidc_discovery_url: data.oidcDiscoveryUrl,
    }),
  });
}

export async function deleteSSOConfig(configId: string): Promise<void> {
  await apiFetch(`/auth/sso/config/${configId}`, { method: 'DELETE' });
}

export async function testSSOConnection(): Promise<SSOTestResult> {
  return apiFetch<SSOTestResult>('/auth/sso/config/test', { method: 'POST' });
}

export async function toggleSSOEnforcement(enforce: boolean): Promise<void> {
  await apiFetch('/auth/sso/enforce', {
    method: 'PATCH',
    body: JSON.stringify({ enforce }),
  });
}

// ─── SSO Login Flow ─────────────────────────────────────────────────────────

export async function checkSSORequirement(email: string): Promise<SSOCheckResult> {
  return apiFetch<SSOCheckResult>(`/auth/sso/check?email=${encodeURIComponent(email)}`);
}

export function getSSOInitiateUrl(orgSlug: string): string {
  return apiUrl(`/auth/sso/initiate/${orgSlug}`);
}
