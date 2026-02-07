/** SSO configuration and auth flow types. */

export interface SSOConfig {
  id: string;
  orgId: string;
  providerType: 'saml' | 'oidc';
  enabled: boolean;

  // SAML
  samlEntityId?: string | null;
  samlSsoUrl?: string | null;
  samlX509Cert?: string | null;

  // OIDC
  oidcIssuer?: string | null;
  oidcClientId?: string | null;
  oidcClientSecretSet: boolean;
  oidcDiscoveryUrl?: string | null;

  createdAt: string;
  updatedAt: string;
}

export interface SSOConfigCreate {
  providerType: 'saml' | 'oidc';
  samlEntityId?: string;
  samlSsoUrl?: string;
  samlX509Cert?: string;
  samlMetadataXml?: string;
  oidcIssuer?: string;
  oidcClientId?: string;
  oidcClientSecret?: string;
  oidcDiscoveryUrl?: string;
}

export interface SSOConfigUpdate {
  enabled?: boolean;
  samlEntityId?: string;
  samlSsoUrl?: string;
  samlX509Cert?: string;
  samlMetadataXml?: string;
  oidcIssuer?: string;
  oidcClientId?: string;
  oidcClientSecret?: string;
  oidcDiscoveryUrl?: string;
}

export interface SSOTestResult {
  success: boolean;
  message: string;
}

export interface SSOCheckResult {
  sso_required: boolean;
  org_slug?: string;
}
