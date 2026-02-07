/**
 * Organizations API client functions.
 */

import { apiFetch } from './client';

export async function updateOrgSettings(
  settings: Record<string, unknown>,
): Promise<void> {
  await apiFetch('/organizations/current', {
    method: 'PATCH',
    body: JSON.stringify({ settings }),
  });
}

export interface RegionInfo {
  id: string;
  name: string;
  country: string;
}

export interface ProviderRegionRule {
  region: string;
  allowedProviders: string[];
}

export interface DataResidencyConfig {
  primaryRegion: string;
  allowedRegions: string[];
  providerRules: ProviderRegionRule[];
  enforceResidency: boolean;
  encryptionKeyId: string | null;
}

export interface DataResidencyResponse {
  config: DataResidencyConfig;
  availableRegions: RegionInfo[];
}

export async function getDataResidency(): Promise<DataResidencyResponse> {
  return apiFetch<DataResidencyResponse>('/organizations/current/data-residency');
}

export async function updateDataResidency(
  data: Partial<DataResidencyConfig>,
): Promise<DataResidencyResponse> {
  return apiFetch<DataResidencyResponse>('/organizations/current/data-residency', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}
