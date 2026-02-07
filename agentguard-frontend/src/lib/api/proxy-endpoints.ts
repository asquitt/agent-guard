/**
 * Proxy Endpoints API client functions.
 */

import type { ProxyEndpoint } from '@/types';
import { apiFetch } from './client';

export async function createProxyEndpoint(body: {
  name: string;
  provider: string;
  target_url: string;
}): Promise<ProxyEndpoint> {
  return apiFetch<ProxyEndpoint>('/proxy-endpoints/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
