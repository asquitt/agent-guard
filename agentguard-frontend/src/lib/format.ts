/**
 * Formatting utilities.
 */

const MINUTE = 60;
const HOUR = MINUTE * 60;
const DAY = HOUR * 24;
const WEEK = DAY * 7;
const MONTH = DAY * 30;

/**
 * Format a date as relative time (e.g. "2 hours ago", "3 days ago").
 * Falls back to locale date for anything older than 30 days.
 */
export function timeAgo(dateInput: string | Date): string {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  const now = Date.now();
  const seconds = Math.floor((now - date.getTime()) / 1000);

  if (seconds < 0) return 'just now';
  if (seconds < MINUTE) return 'just now';
  if (seconds < HOUR) {
    const m = Math.floor(seconds / MINUTE);
    return `${m}m ago`;
  }
  if (seconds < DAY) {
    const h = Math.floor(seconds / HOUR);
    return `${h}h ago`;
  }
  if (seconds < WEEK) {
    const d = Math.floor(seconds / DAY);
    return `${d}d ago`;
  }
  if (seconds < MONTH) {
    const w = Math.floor(seconds / WEEK);
    return `${w}w ago`;
  }
  return date.toLocaleDateString();
}

/**
 * Format a number with commas (e.g. 1234567 -> "1,234,567").
 */
export function formatNumber(n: number): string {
  return n.toLocaleString();
}

/**
 * Format USD currency (e.g. 12.5 -> "$12.50").
 */
export function formatUsd(amount: number, decimals: number = 2): string {
  return `$${amount.toFixed(decimals)}`;
}

/**
 * Format a date as short date (e.g. "Feb 14, 2026").
 */
export function formatDate(dateInput: string | Date): string {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format a date as short datetime (e.g. "Feb 14, 2026 2:30 PM").
 */
export function formatDateTime(dateInput: string | Date): string {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}
