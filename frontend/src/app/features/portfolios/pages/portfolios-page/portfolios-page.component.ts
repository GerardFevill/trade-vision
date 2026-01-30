import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { Mt5ApiService } from '@app/data-access';
import { PortfolioSummary, PORTFOLIO_TYPES, PortfolioType } from '@app/data-access/models/portfolio.model';
import { formatCurrency, formatPercentSigned, getProfitClass } from '@app/shared';
import { PortfolioCardComponent } from '../../ui/portfolio-card/portfolio-card.component';
import { PortfolioFormComponent } from '../../ui/portfolio-form/portfolio-form.component';

type ClientFilter = 'all' | string;

@Component({
  selector: 'app-portfolios-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    PortfolioCardComponent,
    PortfolioFormComponent
  ],
  templateUrl: './portfolios-page.component.html',
  styleUrl: './portfolios-page.component.scss'
})
export class PortfoliosPageComponent implements OnInit {
  // State
  portfolios = signal<PortfolioSummary[]>([]);
  clients = signal<string[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  clientFilter = signal<ClientFilter>('all');
  showCreateModal = signal<boolean>(false);

  // Template helpers
  fmt = { formatCurrency, formatPercentSigned, getProfitClass };

  // Computed
  filteredPortfolios = computed(() => {
    const filter = this.clientFilter();
    if (filter === 'all') return this.portfolios();
    return this.portfolios().filter(p => p.client === filter);
  });

  totalBalance = computed(() =>
    this.filteredPortfolios().reduce((sum, p) => sum + p.total_balance, 0)
  );

  totalProfit = computed(() =>
    this.filteredPortfolios().reduce((sum, p) => sum + p.total_profit, 0)
  );

  totalAccounts = computed(() =>
    this.filteredPortfolios().reduce((sum, p) => sum + p.account_count, 0)
  );

  portfoliosByClient = computed(() => {
    const grouped: Record<string, PortfolioSummary[]> = {};
    for (const p of this.filteredPortfolios()) {
      if (!grouped[p.client]) grouped[p.client] = [];
      grouped[p.client].push(p);
    }
    return grouped;
  });

  constructor(
    private router: Router,
    private api: Mt5ApiService
  ) {}

  ngOnInit(): void {
    this.loadPortfolios();
    this.loadClients();
  }

  loadPortfolios(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getPortfolios().subscribe({
      next: (portfolios) => {
        this.portfolios.set(portfolios);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Impossible de charger les portefeuilles');
        this.loading.set(false);
      }
    });
  }

  loadClients(): void {
    this.api.getPortfolioClients().subscribe({
      next: (clients) => this.clients.set(clients),
      error: () => {}
    });
  }

  setClientFilter(filter: ClientFilter): void {
    this.clientFilter.set(filter);
  }

  openPortfolio(portfolio: PortfolioSummary): void {
    this.router.navigate(['/portfolios', portfolio.id]);
  }

  openCreateModal(): void {
    this.showCreateModal.set(true);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
  }

  onPortfolioCreated(): void {
    this.closeCreateModal();
    this.loadPortfolios();
    this.loadClients();
  }

  deletePortfolio(portfolio: PortfolioSummary, event: Event): void {
    event.stopPropagation();
    if (!confirm(`Supprimer le portefeuille "${portfolio.name}" ?`)) return;

    this.api.deletePortfolio(portfolio.id).subscribe({
      next: () => this.loadPortfolios(),
      error: () => this.error.set('Impossible de supprimer le portefeuille')
    });
  }

  getTypeClass(type: string): string {
    switch (type) {
      case 'Conservateur': return 'type-conservateur';
      case 'Modere': return 'type-modere';
      case 'Agressif': return 'type-agressif';
      default: return '';
    }
  }
}
