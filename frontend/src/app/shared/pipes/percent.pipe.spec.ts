import { describe, it, expect } from 'vitest';
import { PercentPipe } from './percent.pipe';

describe('PercentPipe', () => {
  const pipe = new PercentPipe();

  it('formats unsigned percent', () => {
    expect(pipe.transform(12.345)).toBe('12.35%');
  });

  it('formats signed positive percent', () => {
    expect(pipe.transform(5.5, true)).toBe('+5.50%');
  });

  it('formats signed negative percent', () => {
    expect(pipe.transform(-3.2, true)).toBe('-3.20%');
  });

  it('returns dash for null', () => {
    expect(pipe.transform(null)).toBe('-');
  });
});
