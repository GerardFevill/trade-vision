import { describe, it, expect } from 'vitest';
import { CurrencyPipe } from './currency.pipe';

describe('CurrencyPipe', () => {
  const pipe = new CurrencyPipe();

  it('formats EUR value', () => {
    const result = pipe.transform(1234.5, 'EUR');
    expect(result).toContain('€');
  });

  it('formats USD value', () => {
    const result = pipe.transform(100, 'USD');
    expect(result).toContain('$');
  });

  it('returns dash for null', () => {
    expect(pipe.transform(null)).toBe('-');
  });
});
