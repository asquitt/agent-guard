/**
 * Organizations API client functions.
 */

import { apiFetch } from './client';

// ── Team Members ───────────────────────────────────────────────

export interface Member {
  id: string;
  email: string;
  name: string;
  role: string;
  isActive: boolean;
  createdAt: string;
}

export interface MemberListResponse {
  items: Member[];
  total: number;
}

export interface RoleInfo {
  role: string;
  permissions: string[];
}

export interface RolesResponse {
  roles: RoleInfo[];
}

export async function listMembers(skip = 0, limit = 50): Promise<MemberListResponse> {
  return apiFetch<MemberListResponse>(
    `/organizations/current/members?skip=${skip}&limit=${limit}`,
  );
}

export async function listRoles(): Promise<RolesResponse> {
  return apiFetch<RolesResponse>('/organizations/roles');
}

export async function updateMemberRole(userId: string, role: string): Promise<Member> {
  return apiFetch<Member>(`/organizations/current/members/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  });
}

export async function removeMember(userId: string): Promise<void> {
  await apiFetch(`/organizations/current/members/${userId}`, {
    method: 'DELETE',
  });
}

export async function inviteMember(email: string, role: string): Promise<Member> {
  return apiFetch<Member>('/organizations/current/members/invite', {
    method: 'POST',
    body: JSON.stringify({ email, role }),
  });
}

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
