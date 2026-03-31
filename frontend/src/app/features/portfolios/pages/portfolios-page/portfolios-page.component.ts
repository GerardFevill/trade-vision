import { Component, signal, computed, OnInit, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { PortfoliosApiService } from '@app/data-access';
import { PortfolioSummary, CurrencyBalance, PORTFOLIO_TYPES, PortfolioType } from '@app/data-access/models/portfolio.model';
import { formatCurrency, formatPercentSigned, getProfitClass } from '@app/shared';
import { FirmStateService } from '@app/core';
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
  private readonly firmState = inject(FirmStateService);

  // State
  portfolios = signal<PortfolioSummary[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  clientFilter = signal<ClientFilter>('all');
  showCreateModal = signal<boolean>(false);
  viewMode = signal<'cards' | 'list'>('cards');
  hiddenIds = signal<Set<number>>(new Set());
  showHidden = signal<boolean>(false);

  // Template helpers
  fmt = { formatCurrency, formatPercentSigned, getProfitClass };

  // Dynamic profiles from FirmStateService
  profiles = computed(() => this.firmState.profileNames());

  // Computed
  filteredPortfolios = computed(() => {
    const filter = this.clientFilter();
    const hidden = this.hiddenIds();
    const showAll = this.showHidden();
    const profileList = this.profiles();
    let list = this.portfolios();

    if (filter !== 'all') {
      list = list.filter(p => p.client === filter);
    } else if (profileList.length > 0) {
      list = list.filter(p => profileList.includes(p.client));
    }

    if (!showAll && hidden.size > 0) {
      list = list.filter(p => !hidden.has(p.id));
    }
    // Sort by type: Agressif → Modere → Conservateur → Securise
    return [...list].sort((a, b) => getTypeOrder(a.type) - getTypeOrder(b.type));
  });

  // Securise portfolios
  securisePortfolios = computed(() =>
    this.filteredPortfolios().filter(p => p.type.toLowerCase() === 'securise')
  );

  securiseAccounts = computed(() =>
    this.securisePortfolios().reduce((sum, p) => sum + p.account_count, 0)
  );

  securiseBalancesByCurrency = computed(() =>
    this.aggregateByCurrency(this.securisePortfolios())
  );

  // Trading portfolios (Agressif, Modere, Conservateur)
  tradingPortfolios = computed(() =>
    this.filteredPortfolios().filter(p => p.type.toLowerCase() !== 'securise')
  );

  tradingAccounts = computed(() =>
    this.tradingPortfolios().reduce((sum, p) => sum + p.account_count, 0)
  );

  tradingBalancesByCurrency = computed(() =>
    this.aggregateByCurrency(this.tradingPortfolios())
  );

  totalBalancesByCurrency = computed(() =>
    this.aggregateByCurrency(this.filteredPortfolios())
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

  private aggregateByCurrency(portfolios: PortfolioSummary[]): CurrencyBalance[] {
    const map = new Map<string, { balance: number; profit: number }>();
    for (const p of portfolios) {
      if (p.balances_by_currency?.length) {
        for (const cb of p.balances_by_currency) {
          const existing = map.get(cb.currency);
          if (existing) {
            existing.balance += cb.balance;
            existing.profit += cb.profit;
          } else {
            map.set(cb.currency, { balance: cb.balance, profit: cb.profit });
          }
        }
      } else {
        // Fallback: use total with EUR
        const existing = map.get('EUR');
        if (existing) {
          existing.balance += p.total_balance;
          existing.profit += p.total_profit;
        } else {
          map.set('EUR', { balance: p.total_balance, profit: p.total_profit });
        }
      }
    }
    return Array.from(map.entries()).map(([currency, v]) => ({
      currency, balance: v.balance, profit: v.profit
    }));
  }

  constructor(
    private router: Router,
    private portfoliosApi: PortfoliosApiService
  ) {
    // Reset filter when firm changes
    effect(() => {
      this.firmState.selectedFirmId();
      this.clientFilter.set('all');
    });
  }

  ngOnInit(): void {
    this.loadHiddenIds();
    this.loadPortfolios();
  }

  loadPortfolios(): void {
    this.loading.set(true);
    this.error.set(null);
    this.portfoliosApi.getPortfolios().subscribe({
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

  setClientFilter(filter: ClientFilter): void {
    this.clientFilter.set(filter);
  }

  setViewMode(mode: 'cards' | 'list'): void {
    this.viewMode.set(mode);
  }

  openPortfolio(portfolio: PortfolioSummary): void {
    const slug = this.firmState.selectedFirmSlug();
    this.router.navigate([`/${slug}/portifs`, portfolio.id]);
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
    this.firmState.loadFirms();
  }

  deletePortfolio(portfolio: PortfolioSummary, event: Event): void {
    event.stopPropagation();
    if (!confirm(`Supprimer le portefeuille "${portfolio.name}" ?`)) return;

    this.portfoliosApi.deletePortfolio(portfolio.id).subscribe({
      next: () => this.loadPortfolios(),
      error: () => this.error.set('Impossible de supprimer le portefeuille')
    });
  }

  hidePortfolio(portfolio: PortfolioSummary, event: Event): void {
    event.stopPropagation();
    const ids = new Set(this.hiddenIds());
    if (ids.has(portfolio.id)) {
      ids.delete(portfolio.id);
    } else {
      ids.add(portfolio.id);
    }
    this.hiddenIds.set(ids);
    this.saveHiddenIds(ids);
  }

  toggleShowHidden(): void {
    this.showHidden.update(v => !v);
  }

  private loadHiddenIds(): void {
    try {
      const stored = localStorage.getItem('elite_hidden_portfolios');
      if (stored) {
        this.hiddenIds.set(new Set(JSON.parse(stored)));
      }
    } catch {}
  }

  private saveHiddenIds(ids: Set<number>): void {
    localStorage.setItem('elite_hidden_portfolios', JSON.stringify([...ids]));
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
