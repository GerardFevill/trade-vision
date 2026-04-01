import { describe, it, expect, beforeEach, vi } from 'vitest';
import { StorageService } from './storage.service';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock });

describe('StorageService', () => {
  let service: StorageService;

  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    service = new StorageService();
  });

  it('starts with empty favorites', () => {
    expect(service.favorites().size).toBe(0);
  });

  it('toggleFavorite adds an account', () => {
    service.toggleFavorite(123);
    expect(service.isFavorite(123)).toBe(true);
  });

  it('toggleFavorite removes an existing favorite', () => {
    service.toggleFavorite(123);
    service.toggleFavorite(123);
    expect(service.isFavorite(123)).toBe(false);
  });

  it('isFavorite returns false for unknown id', () => {
    expect(service.isFavorite(999)).toBe(false);
  });

  it('persists favorites to localStorage', () => {
    service.toggleFavorite(42);
    expect(localStorageMock.setItem).toHaveBeenCalled();
    const saved = localStorageMock.setItem.mock.calls.find(
      (c: string[]) => c[0] === 'mt5_favorites'
    );
    expect(saved).toBeTruthy();
    const ids = JSON.parse(saved![1]);
    expect(ids).toContain(42);
  });

  it('get returns default when key not found', () => {
    expect(service.get('nonexistent', 'default')).toBe('default');
  });

  it('set and get round-trip', () => {
    service.set('test_key', { a: 1 });
    // Need to make getItem return the stored value
    localStorageMock.getItem.mockReturnValueOnce(JSON.stringify({ a: 1 }));
    expect(service.get('test_key', null)).toEqual({ a: 1 });
  });

  it('remove calls localStorage.removeItem', () => {
    service.remove('some_key');
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('some_key');
  });
});
