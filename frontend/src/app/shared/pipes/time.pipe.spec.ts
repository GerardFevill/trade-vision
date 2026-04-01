import { describe, it, expect } from 'vitest';
import { TimePipe, DatePipe } from './time.pipe';

describe('TimePipe', () => {
  const pipe = new TimePipe();

  it('formats seconds to hours and minutes', () => {
    expect(pipe.transform(7260)).toBe('2h 1m');
  });

  it('formats minutes only when < 1h', () => {
    expect(pipe.transform(1800)).toBe('30m');
  });

  it('returns dash for null', () => {
    expect(pipe.transform(null)).toBe('-');
  });
});

describe('DatePipe', () => {
  const pipe = new DatePipe();

  it('returns dash for null', () => {
    expect(pipe.transform(null)).toBe('-');
  });

  it('formats a date string', () => {
    const result = pipe.transform('2024-06-15T10:30:00');
    // French locale format — should contain day and month
    expect(result).toBeTruthy();
    expect(result).not.toBe('-');
  });
});
