/**
 * Auth API client functions.
 */

import type { AuthTokens, MeResponse } from '@/types';
import { apiFetch, ApiError } from './client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';
const API_PREFIX = '/api/v1';

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
  // Use raw fetch to avoid apiFetch's 401 interceptor triggering a recursive refresh
  const res = await fetch(`${API_BASE_URL}${API_PREFIX}/auth/refresh`, {
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
