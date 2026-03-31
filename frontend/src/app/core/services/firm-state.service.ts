import { Injectable, signal, computed } from '@angular/core';
import { FirmsApiService } from '@app/data-access';
import { FirmWithProfiles } from '@app/data-access/models/firm.model';

const STORAGE_KEY = 'elite_selected_firm';

function toSlug(name: string): string {
  return name.toLowerCase().replace(/\s+/g, '-');
}

@Injectable({ providedIn: 'root' })
export class FirmStateService {
  private readonly firmsApi: FirmsApiService;

  firms = signal<FirmWithProfiles[]>([]);
  selectedFirmId = signal<number | null>(null);

  selectedFirm = computed(() => {
    const id = this.selectedFirmId();
    return id !== null ? this.firms().find(f => f.id === id) ?? null : null;
  });

  selectedFirmSlug = computed(() => {
    const name = this.selectedFirm()?.name;
    return name ? toSlug(name) : null;
  });

  profileNames = computed(() => {
    const firm = this.selectedFirm();
    if (firm) {
      return firm.profiles.map(p => p.name);
    }
    // No firm selected → all profiles from all firms
    return this.firms().flatMap(f => f.profiles.map(p => p.name));
  });

  constructor(firmsApi: FirmsApiService) {
    this.firmsApi = firmsApi;
    this.restoreSelection();
    this.loadFirms();
  }

  loadFirms(): void {
    this.firmsApi.getFirms().subscribe({
      next: (firms) => {
        // Load each firm with profiles
        const loaded: FirmWithProfiles[] = [];
        let remaining = firms.length;
        if (remaining === 0) {
          this.firms.set([]);
          return;
        }
        for (const firm of firms) {
          this.firmsApi.getFirm(firm.id).subscribe({
            next: (full) => {
              loaded.push(full);
              remaining--;
              if (remaining === 0) {
                loaded.sort((a, b) => a.id - b.id);
                this.firms.set(loaded);
              }
            },
            error: () => {
              remaining--;
              if (remaining === 0) {
                loaded.sort((a, b) => a.id - b.id);
                this.firms.set(loaded);
              }
            }
          });
        }
      },
      error: () => {}
    });
  }

  selectFirm(id: number | null): void {
    this.selectedFirmId.set(id);
    if (id !== null) {
      localStorage.setItem(STORAGE_KEY, String(id));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  selectFirmBySlug(slug: string): boolean {
    const firm = this.firms().find(f => toSlug(f.name) === slug.toLowerCase());
    if (firm) {
      this.selectFirm(firm.id);
      return true;
    }
    return false;
  }

  private restoreSelection(): void {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        this.selectedFirmId.set(Number(stored));
      }
    } catch {}
  }
}
