import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ConnectionStateService {
  readonly backendOnline = signal<boolean>(true);
  readonly lastError = signal<string | null>(null);

  markOffline(error?: string): void {
    this.backendOnline.set(false);
    this.lastError.set(error ?? 'Backend indisponible');
  }

  markOnline(): void {
    this.backendOnline.set(true);
    this.lastError.set(null);
  }
}
