/** Shared UI constants for AgentGuard dashboard. */

export const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-danger-50 text-danger-600',
  high: 'bg-red-50 text-red-600',
  medium: 'bg-warning-50 text-warning-600',
  low: 'bg-blue-50 text-blue-600',
  info: 'bg-gray-100 text-gray-600',
};

export const SEVERITY_COLORS_BORDERED: Record<string, string> = {
  critical: 'bg-danger-50 text-danger-600 border-danger-200',
  high: 'bg-red-50 text-red-600 border-red-200',
  medium: 'bg-warning-50 text-warning-600 border-warning-200',
  low: 'bg-blue-50 text-blue-600 border-blue-200',
  info: 'bg-gray-50 text-gray-600 border-gray-200',
};

export const STATUS_COLORS: Record<string, string> = {
  open: 'bg-danger-50 text-danger-600',
  acknowledged: 'bg-warning-50 text-warning-600',
  resolved: 'bg-success-50 text-success-600',
  dismissed: 'bg-gray-100 text-gray-500',
};
