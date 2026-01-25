import { Injectable, signal } from '@angular/core';

/**
 * Core singleton service for browser storage management
 * Used across the entire application for persistent state
 */
@Injectable({ providedIn: 'root' })
export class StorageService {
  private readonly FAVORITES_KEY = 'mt5_favorites';

  readonly favorites = signal<Set<number>>(new Set());

  constructor() {
    this.loadFavorites();
  }

  private loadFavorites(): void {
    try {
      const stored = localStorage.getItem(this.FAVORITES_KEY);
      if (stored) {
        const ids = JSON.parse(stored) as number[];
        this.favorites.set(new Set(ids));
      }
    } catch (e) {
      console.error('Error loading favorites:', e);
    }
  }

  private saveFavorites(): void {
    try {
      const ids = Array.from(this.favorites());
      localStorage.setItem(this.FAVORITES_KEY, JSON.stringify(ids));
    } catch (e) {
      console.error('Error saving favorites:', e);
    }
  }

  toggleFavorite(accountId: number): void {
    const favs = new Set(this.favorites());
    if (favs.has(accountId)) {
      favs.delete(accountId);
    } else {
      favs.add(accountId);
    }
    this.favorites.set(favs);
    this.saveFavorites();
  }

  isFavorite(accountId: number): boolean {
    return this.favorites().has(accountId);
  }

  getFavorites(): Set<number> {
    return this.favorites();
  }

  // Generic storage methods
  get<T>(key: string, defaultValue: T): T {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  }

  set<T>(key: string, value: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.error(`Error saving ${key}:`, e);
    }
  }

  remove(key: string): void {
    localStorage.removeItem(key);
  }
}
