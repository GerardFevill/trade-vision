import { Component, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { Mt5ApiService } from '@app/data-access';
import { PortfolioType, PORTFOLIO_TYPES, CreatePortfolioRequest } from '@app/data-access/models/portfolio.model';

@Component({
  selector: 'app-portfolio-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './portfolio-form.component.html',
  styleUrl: './portfolio-form.component.scss'
})
export class PortfolioFormComponent {
  @Output() created = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();

  // Form state
  name = signal<string>('');
  type = signal<PortfolioType>('Securise');
  client = signal<string>('');
  loading = signal<boolean>(false);
  error = signal<string | null>(null);

  // Options
  portfolioTypes: PortfolioType[] = ['Securise', 'Conservateur', 'Modere', 'Agressif'];
  clients: string[] = ['Akaj', 'CosmosElite'];

  constructor(private api: Mt5ApiService) {}

  getFactorsForType(type: PortfolioType): number[] {
    return PORTFOLIO_TYPES[type] || [];
  }

  getTypeDescription(type: PortfolioType): string {
    switch (type) {
      case 'Securise': return 'Sans multiplicateur - Comptes illimites';
      case 'Conservateur': return 'Risque faible - Facteurs 0.2x a 1.8x';
      case 'Modere': return 'Risque modere - Facteur 2.0x (x10)';
      case 'Agressif': return 'Risque eleve - Facteurs 2.5x a 4.5x';
      default: return '';
    }
  }

  onSubmit(): void {
    if (!this.name() || !this.type() || !this.client()) {
      this.error.set('Veuillez remplir tous les champs');
      return;
    }

    this.loading.set(true);
    this.error.set(null);

    const request: CreatePortfolioRequest = {
      name: this.name(),
      type: this.type(),
      client: this.client()
    };

    this.api.createPortfolio(request).subscribe({
      next: () => {
        this.loading.set(false);
        this.created.emit();
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err.error?.detail || 'Erreur lors de la creation');
      }
    });
  }

  onCancel(): void {
    this.cancelled.emit();
  }
}
