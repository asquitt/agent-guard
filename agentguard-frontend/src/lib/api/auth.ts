/**
 * Auth API client functions.
 */

import type { AuthTokens, MeResponse } from '@/types';
import { apiFetch } from './client';

export async function loginApi(
  email: string,
  password: string,
): Promise<AuthTokens> {
  return apiFetch<AuthTokens>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function registerApi(
  email: string,
  password: string,
  fullName: string,
  orgName: string,
): Promise<AuthTokens> {
  return apiFetch<AuthTokens>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
      org_name: orgName,
    }),
  });
}

export async function refreshTokenApi(
  refreshToken: string,
): Promise<AuthTokens> {
  return apiFetch<AuthTokens>('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function getMeApi(): Promise<MeResponse> {
  return apiFetch<MeResponse>('/auth/me');
}

export async function logoutApi(): Promise<void> {
  await apiFetch<void>('/auth/logout', { method: 'POST' });
}
