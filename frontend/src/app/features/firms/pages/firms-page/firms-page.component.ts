import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { FirmsApiService, Firm, FirmWithProfiles, Profile } from '@app/data-access';

@Component({
  selector: 'app-firms-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './firms-page.component.html',
  styleUrl: './firms-page.component.scss'
})
export class FirmsPageComponent implements OnInit {
  firms = signal<FirmWithProfiles[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);

  // Create firm form
  showFirmForm = signal<boolean>(false);
  newFirmName = signal<string>('');
  creatingFirm = signal<boolean>(false);

  // Create profile form
  showProfileForm = signal<number | null>(null); // firm ID or null
  newProfileName = signal<string>('');
  creatingProfile = signal<boolean>(false);

  totalProfiles = computed(() =>
    this.firms().reduce((sum, f) => sum + f.profiles.length, 0)
  );

  constructor(private firmsApi: FirmsApiService) {}

  ngOnInit(): void {
    this.loadFirms();
  }

  loadFirms(): void {
    this.loading.set(true);
    this.error.set(null);
    this.firmsApi.getFirms().subscribe({
      next: (firms) => {
        // Load each firm with profiles
        const loaded: FirmWithProfiles[] = [];
        let remaining = firms.length;
        if (remaining === 0) {
          this.firms.set([]);
          this.loading.set(false);
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
                this.loading.set(false);
              }
            },
            error: () => {
              remaining--;
              if (remaining === 0) {
                loaded.sort((a, b) => a.id - b.id);
                this.firms.set(loaded);
                this.loading.set(false);
              }
            }
          });
        }
      },
      error: () => {
        this.error.set('Impossible de charger les firms');
        this.loading.set(false);
      }
    });
  }

  // --- Firm CRUD ---

  openFirmForm(): void {
    this.newFirmName.set('');
    this.showFirmForm.set(true);
  }

  closeFirmForm(): void {
    this.showFirmForm.set(false);
  }

  createFirm(): void {
    const name = this.newFirmName().trim();
    if (!name) return;

    this.creatingFirm.set(true);
    this.firmsApi.createFirm({ name }).subscribe({
      next: () => {
        this.creatingFirm.set(false);
        this.closeFirmForm();
        this.loadFirms();
      },
      error: (err) => {
        this.creatingFirm.set(false);
        this.error.set(err.error?.detail || 'Erreur lors de la creation');
      }
    });
  }

  deleteFirm(firm: FirmWithProfiles): void {
    if (!confirm(`Supprimer "${firm.name}" et tous ses profils ?`)) return;

    this.firmsApi.deleteFirm(firm.id).subscribe({
      next: () => this.loadFirms(),
      error: () => this.error.set('Impossible de supprimer la firm')
    });
  }

  // --- Profile CRUD ---

  openProfileForm(firmId: number): void {
    this.newProfileName.set('');
    this.showProfileForm.set(firmId);
  }

  closeProfileForm(): void {
    this.showProfileForm.set(null);
  }

  createProfile(firmId: number): void {
    const name = this.newProfileName().trim();
    if (!name) return;

    this.creatingProfile.set(true);
    this.firmsApi.createProfile({ name, firm_id: firmId }).subscribe({
      next: () => {
        this.creatingProfile.set(false);
        this.closeProfileForm();
        this.loadFirms();
      },
      error: (err) => {
        this.creatingProfile.set(false);
        this.error.set(err.error?.detail || 'Erreur lors de la creation du profil');
      }
    });
  }

  deleteProfile(profile: Profile, event: Event): void {
    event.stopPropagation();
    if (profile.is_default) return;
    if (!confirm(`Supprimer le profil "${profile.name}" ?`)) return;

    this.firmsApi.deleteProfile(profile.id).subscribe({
      next: () => this.loadFirms(),
      error: () => this.error.set('Impossible de supprimer le profil')
    });
  }
}
