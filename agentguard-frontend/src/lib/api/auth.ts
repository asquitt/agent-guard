/**
 * Auth API client functions.
 */

import type { AuthTokens, LoginResponse, MeResponse, MfaSetupResponse } from '@/types';
import { apiFetch, ApiError } from './client';
import { apiUrl } from './url';

export interface RegisterInput {
  email: string;
  password: string;
  fullName: string;
  orgName: string;
  controlledEvaluationAccepted: true;
  accessCode?: string;
}

export async function loginApi(
  email: string,
  password: string,
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function verifyMfaLoginApi(
  mfaToken: string,
  code: string,
): Promise<AuthTokens> {
  return apiFetch<AuthTokens>('/auth/mfa/verify-login', {
    method: 'POST',
    body: JSON.stringify({ mfa_token: mfaToken, code }),
  });
}

export async function setupMfaApi(): Promise<MfaSetupResponse> {
  return apiFetch<MfaSetupResponse>('/auth/mfa/setup', {
    method: 'POST',
  });
}

export async function confirmMfaSetupApi(code: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>('/auth/mfa/confirm-setup', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

export async function disableMfaApi(code: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>('/auth/mfa/disable', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

export async function registerApi(input: RegisterInput): Promise<AuthTokens> {
  return apiFetch<AuthTokens>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email: input.email,
      password: input.password,
      full_name: input.fullName,
      org_name: input.orgName,
      controlled_evaluation_accepted: input.controlledEvaluationAccepted,
      access_code: input.accessCode || undefined,
    }),
  });
}

export async function refreshTokenApi(
  refreshToken: string,
): Promise<AuthTokens> {
  // Use raw fetch to avoid apiFetch's 401 interceptor triggering a recursive refresh
  const res = await fetch(apiUrl('/auth/refresh'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) throw new ApiError(res.status, 'Token refresh failed');
  return res.json();
}

export async function getMeApi(): Promise<MeResponse> {
  return apiFetch<MeResponse>('/auth/me');
}

export async function logoutApi(): Promise<void> {
  await apiFetch<void>('/auth/logout', { method: 'POST' });
}

export async function forgotPasswordApi(email: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export async function resetPasswordApi(
  token: string,
  newPassword: string,
): Promise<AuthTokens> {
  return apiFetch<AuthTokens>('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: string;
  organizationId: string;
  isActive: boolean;
  createdAt: string;
}

export async function updateProfileApi(data: { full_name?: string }): Promise<UserProfile> {
  return apiFetch<UserProfile>('/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}
