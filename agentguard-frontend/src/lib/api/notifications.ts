import { apiFetch } from './client';

export interface NotificationPreferences {
  email_enabled: boolean;
  email_digest: 'realtime' | 'hourly' | 'daily' | 'weekly' | 'off';
  min_severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  categories: string[];
  in_app_enabled: boolean;
  slack_dm_enabled: boolean;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

interface NotificationPreferencesResponse {
  preferences: NotificationPreferences;
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const res = await apiFetch<NotificationPreferencesResponse>('/auth/me/notifications');
  return res.preferences;
}

export async function updateNotificationPreferences(
  prefs: NotificationPreferences,
): Promise<NotificationPreferences> {
  const res = await apiFetch<NotificationPreferencesResponse>('/auth/me/notifications', {
    method: 'PUT',
    body: JSON.stringify(prefs),
  });
  return res.preferences;
}
