import { describe, it, expect } from 'vitest';
import {
  formatNumber,
  formatCurrency,
  formatPercent,
  formatPercentSigned,
  formatTime,
  getProfitClass,
  getDrawdownClass,
  getPerformanceClass,
  getBarPercent,
} from './format.utils';

// --- formatNumber ---
describe('formatNumber', () => {
  it('formats a positive number with 2 decimals', () => {
    expect(formatNumber(1234.567)).toBe('1234.57');
  });

  it('formats zero', () => {
    expect(formatNumber(0)).toBe('0.00');
  });

  it('formats with custom decimals', () => {
    expect(formatNumber(3.14159, 4)).toBe('3.1416');
  });

  it('returns dash for null', () => {
    expect(formatNumber(null)).toBe('-');
  });

  it('returns dash for undefined', () => {
    expect(formatNumber(undefined)).toBe('-');
  });
});

// --- formatCurrency ---
describe('formatCurrency', () => {
  it('formats EUR by default', () => {
    const result = formatCurrency(1234.5);
    // French locale uses non-breaking space
    expect(result).toContain('€');
  });

  it('formats USD', () => {
    const result = formatCurrency(100, 'USD');
    expect(result).toContain('$');
  });

  it('returns dash for null', () => {
    expect(formatCurrency(null)).toBe('-');
  });

  it('returns dash for undefined', () => {
    expect(formatCurrency(undefined)).toBe('-');
  });
});

// --- formatPercent ---
describe('formatPercent', () => {
  it('formats a positive percent', () => {
    expect(formatPercent(12.345)).toBe('12.35%');
  });

  it('formats zero', () => {
    expect(formatPercent(0)).toBe('0.00%');
  });

  it('returns dash for null', () => {
    expect(formatPercent(null)).toBe('-');
  });
});

// --- formatPercentSigned ---
describe('formatPercentSigned', () => {
  it('adds + for positive', () => {
    expect(formatPercentSigned(5.5)).toBe('+5.50%');
  });

  it('no + for negative', () => {
    expect(formatPercentSigned(-3.2)).toBe('-3.20%');
  });

  it('adds + for zero', () => {
    expect(formatPercentSigned(0)).toBe('+0.00%');
  });

  it('returns dash for null', () => {
    expect(formatPercentSigned(null)).toBe('-');
  });
});

// --- formatTime ---
describe('formatTime', () => {
  it('formats hours and minutes', () => {
    expect(formatTime(7260)).toBe('2h 1m');
  });

  it('formats minutes only when < 1h', () => {
    expect(formatTime(1800)).toBe('30m');
  });

  it('returns dash for 0', () => {
    expect(formatTime(0)).toBe('-');
  });

  it('returns dash for null', () => {
    expect(formatTime(null)).toBe('-');
  });
});

// --- getProfitClass ---
describe('getProfitClass', () => {
  it('returns positive for profit > 0', () => {
    expect(getProfitClass(100)).toBe('positive');
  });

  it('returns positive for zero', () => {
    expect(getProfitClass(0)).toBe('positive');
  });

  it('returns negative for loss', () => {
    expect(getProfitClass(-50)).toBe('negative');
  });

  it('returns empty string for null', () => {
    expect(getProfitClass(null)).toBe('');
  });
});

// --- getDrawdownClass ---
describe('getDrawdownClass', () => {
  it('returns dd-critical for >= 50', () => {
    expect(getDrawdownClass(50)).toBe('dd-critical');
  });

  it('returns dd-warning for >= 30', () => {
    expect(getDrawdownClass(35)).toBe('dd-warning');
  });

  it('returns dd-moderate for >= 10', () => {
    expect(getDrawdownClass(15)).toBe('dd-moderate');
  });

  it('returns dd-low for < 10', () => {
    expect(getDrawdownClass(5)).toBe('dd-low');
  });

  it('returns empty string for null', () => {
    expect(getDrawdownClass(null)).toBe('');
  });
});

// --- getPerformanceClass ---
describe('getPerformanceClass', () => {
  it('returns perf-excellent for >= 50', () => {
    expect(getPerformanceClass(75)).toBe('perf-excellent');
  });

  it('returns perf-good for >= 20', () => {
    expect(getPerformanceClass(25)).toBe('perf-good');
  });

  it('returns perf-neutral for >= 0', () => {
    expect(getPerformanceClass(5)).toBe('perf-neutral');
  });

  it('returns perf-warning for >= -20', () => {
    expect(getPerformanceClass(-10)).toBe('perf-warning');
  });

  it('returns perf-danger for < -20', () => {
    expect(getPerformanceClass(-30)).toBe('perf-danger');
  });
});

// --- getBarPercent ---
describe('getBarPercent', () => {
  it('calculates percentage correctly', () => {
    expect(getBarPercent(50, 100)).toBe(50);
  });

  it('caps at 100', () => {
    expect(getBarPercent(200, 100)).toBe(100);
  });

  it('floors at 0', () => {
    expect(getBarPercent(-10, 100)).toBe(0);
  });

  it('returns 0 for null value', () => {
    expect(getBarPercent(null, 100)).toBe(0);
  });

  it('returns 0 for max=0', () => {
    expect(getBarPercent(50, 0)).toBe(0);
  });
});
