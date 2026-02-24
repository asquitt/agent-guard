import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { timeAgo, formatNumber, formatUsd, formatDate } from '../format';

describe('timeAgo', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "just now" for recent timestamps', () => {
    expect(timeAgo('2024-06-15T11:59:50Z')).toBe('just now');
  });

  it('returns minutes ago', () => {
    expect(timeAgo('2024-06-15T11:55:00Z')).toBe('5m ago');
  });

  it('returns hours ago', () => {
    expect(timeAgo('2024-06-15T09:00:00Z')).toBe('3h ago');
  });

  it('returns days ago', () => {
    expect(timeAgo('2024-06-13T12:00:00Z')).toBe('2d ago');
  });

  it('returns weeks ago', () => {
    expect(timeAgo('2024-06-01T12:00:00Z')).toBe('2w ago');
  });

  it('returns locale date for old timestamps', () => {
    const result = timeAgo('2024-01-15T12:00:00Z');
    // The locale date will contain some form of "2024"
    expect(result).toMatch(/1\/15\/2024|Jan.*15.*2024|15.*Jan.*2024/);
  });

  it('handles Date objects', () => {
    expect(timeAgo(new Date('2024-06-15T11:58:00Z'))).toBe('2m ago');
  });

  it('returns "just now" for future timestamps', () => {
    expect(timeAgo('2024-06-15T13:00:00Z')).toBe('just now');
  });
});

describe('formatNumber', () => {
  it('formats with commas', () => {
    expect(formatNumber(1234567)).toBe('1,234,567');
  });

  it('formats small numbers without commas', () => {
    expect(formatNumber(42)).toBe('42');
  });
});

describe('formatUsd', () => {
  it('formats as USD currency', () => {
    expect(formatUsd(12.5)).toBe('$12.50');
  });

  it('supports custom decimal places', () => {
    expect(formatUsd(12.555, 3)).toBe('$12.555');
  });
});

describe('formatDate', () => {
  it('formats date string', () => {
    const result = formatDate('2026-02-14T12:00:00Z');
    expect(result).toContain('Feb');
    expect(result).toContain('2026');
  });

  it('formats Date object', () => {
    const result = formatDate(new Date('2026-02-14'));
    expect(result).toContain('Feb');
  });
});
