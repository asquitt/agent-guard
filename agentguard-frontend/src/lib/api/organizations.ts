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
