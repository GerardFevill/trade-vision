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

// Order: most aggressive to most secure
const TYPE_ORDER: Record<string, number> = {
  'agressif': 0,
  'modere': 1,
  'conservateur': 2,
  'securise': 3,
};

function getTypeOrder(type: string): number {
  return TYPE_ORDER[type.toLowerCase()] ?? 99;
}

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
  viewMode = signal<'cards' | 'list'>('cards');

  // Template helpers
  fmt = { formatCurrency, formatPercentSigned, getProfitClass };

  // Computed
  filteredPortfolios = computed(() => {
    const filter = this.clientFilter();
    let list = this.portfolios();
    if (filter !== 'all') {
      list = list.filter(p => p.client === filter);
    }
    // Sort by type: Agressif → Modere → Conservateur → Securise
    return [...list].sort((a, b) => getTypeOrder(a.type) - getTypeOrder(b.type));
  });

  // Securise portfolios
  securisePortfolios = computed(() =>
    this.filteredPortfolios().filter(p => p.type.toLowerCase() === 'securise')
  );

  securiseBalance = computed(() =>
    this.securisePortfolios().reduce((sum, p) => sum + p.total_balance, 0)
  );

  securiseProfit = computed(() =>
    this.securisePortfolios().reduce((sum, p) => sum + p.total_profit, 0)
  );

  securiseAccounts = computed(() =>
    this.securisePortfolios().reduce((sum, p) => sum + p.account_count, 0)
  );

  // Trading portfolios (Agressif, Modere, Conservateur)
  tradingPortfolios = computed(() =>
    this.filteredPortfolios().filter(p => p.type.toLowerCase() !== 'securise')
  );

  tradingBalance = computed(() =>
    this.tradingPortfolios().reduce((sum, p) => sum + p.total_balance, 0)
  );

  tradingProfit = computed(() =>
    this.tradingPortfolios().reduce((sum, p) => sum + p.total_profit, 0)
  );

  tradingAccounts = computed(() =>
    this.tradingPortfolios().reduce((sum, p) => sum + p.account_count, 0)
  );

  portfoliosByClient = computed(() => {
    const grouped: Record<string, PortfolioSummary[]> = {};
    for (const p of this.filteredPortfolios()) {
      if (!grouped[p.client]) grouped[p.client] = [];
      grouped[p.client].push(p);
    }
    // Sort each client's portfolios by type order
    for (const client of Object.keys(grouped)) {
      grouped[client].sort((a, b) => getTypeOrder(a.type) - getTypeOrder(b.type));
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

  setViewMode(mode: 'cards' | 'list'): void {
    this.viewMode.set(mode);
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
      case 'Securise': return 'type-securise';
      case 'Conservateur': return 'type-conservateur';
      case 'Modere': return 'type-modere';
      case 'Agressif': return 'type-agressif';
      default: return '';
    }
  }
}
