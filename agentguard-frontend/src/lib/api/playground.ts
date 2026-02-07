/**
 * Playground API client functions.
 */

import type { PlaygroundTestRequest, PlaygroundTestResponse, PlaygroundCategories } from '@/types';
import { apiFetch } from './client';

export async function testDetectors(
  data: PlaygroundTestRequest,
): Promise<PlaygroundTestResponse> {
  return apiFetch<PlaygroundTestResponse>('/playground/test', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getPlaygroundCategories(): Promise<PlaygroundCategories> {
  return apiFetch<PlaygroundCategories>('/playground/categories');
}
