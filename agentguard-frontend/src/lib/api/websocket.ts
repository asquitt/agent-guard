import { apiFetch } from './client';

export interface WebSocketTicket {
  ticket: string;
  expiresIn: number;
}

export async function createWebSocketTicket(): Promise<WebSocketTicket> {
  return apiFetch<WebSocketTicket>('/ws/ticket', { method: 'POST' });
}
