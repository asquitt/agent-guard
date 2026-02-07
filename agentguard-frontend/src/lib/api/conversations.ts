/**
 * Conversation-level analysis API client functions.
 */

import type { PaginatedResponse } from '@/types';
import { apiFetch, buildQueryString } from './client';

export interface ConversationTurn {
  id: string;
  turnNumber: number;
  role: string;
  contentPreview: string | null;
  riskDelta: number;
  cumulativeRisk: number;
  detections: { category?: string; severity?: string; title?: string }[];
  tokens: number | null;
  proxyRequestId: string | null;
  createdAt: string;
}

export interface Conversation {
  id: string;
  sessionId: string;
  agentId: string | null;
  status: string;
  riskScore: number;
  riskLevel: string;
  turnCount: number;
  totalTokens: number;
  totalCostUsd: number;
  escalatedAt: string | null;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ConversationDetail extends Conversation {
  turns: ConversationTurn[];
}

export interface ConversationFilters {
  status?: string;
  riskLevel?: string;
  agentId?: string;
  skip?: number;
  limit?: number;
}

export interface ConversationStats {
  totalConversations: number;
  activeCount: number;
  escalatedCount: number;
  flaggedCount: number;
  avgRiskScore: number;
  avgTurns: number;
  byRiskLevel: { riskLevel: string; count: number }[];
}

export async function listConversations(
  filters: ConversationFilters = {},
): Promise<PaginatedResponse<Conversation>> {
  const qs = buildQueryString(filters as Record<string, unknown>);
  return apiFetch<PaginatedResponse<Conversation>>(`/conversations${qs}`);
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(`/conversations/${id}`);
}

export async function getConversationStats(days: number = 30): Promise<ConversationStats> {
  return apiFetch<ConversationStats>(`/conversations/stats?days=${days}`);
}

export async function updateConversationStatus(
  id: string,
  status: string,
): Promise<Conversation> {
  return apiFetch<Conversation>(`/conversations/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}
