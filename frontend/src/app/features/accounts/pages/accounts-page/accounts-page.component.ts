import { Component, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { interval, Subscription } from 'rxjs';

import { Mt5ApiService, AccountSummary, SparklineData, GlobalMonthlyGrowth } from '@app/data-access';
import { StorageService } from '@app/core';
import { SparklineComponent, formatCurrency, formatPercentSigned, getProfitClass, getDrawdownClass, getPerformanceClass } from '@app/shared';
import { AccountsHeaderComponent } from '../../ui';

type ViewMode = 'grid' | 'list';
type ClientFilter = 'all' | 'CosmosElite' | 'Akaj';
type SortColumn = 'name' | 'balance' | 'profit' | 'profit_percent' | 'win_rate' | 'drawdown' | 'trades';

/**
 * Accounts Page - Smart/Container component
 * Handles data fetching and state management for accounts list
 */
@Component({
  selector: 'app-accounts-page',
  standalone: true,
  imports: [
    CommonModule,
    AccountsHeaderComponent,
    SparklineComponent
  ],
  templateUrl: './accounts-page.component.html',
  styleUrl: './accounts-page.component.scss'
})
export class AccountsPageComponent implements OnInit, OnDestroy {
  // State
  accounts = signal<AccountSummary[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  viewMode = signal<ViewMode>('grid');
  clientFilter = signal<ClientFilter>('all');
  searchQuery = signal<string>('');
  sortColumn = signal<SortColumn>('balance');
  sortDirection = signal<'asc' | 'desc'>('desc');
  autoRefreshEnabled = signal<boolean>(true);
  lastRefreshTime = signal<Date | null>(null);
  sparklines = signal<SparklineData>({});
  monthlyGrowth = signal<GlobalMonthlyGrowth[]>([]);

  private refreshSubscription?: Subscription;
  private readonly autoRefreshInterval = 5 * 60 * 1000;

  // Template helpers
  fmt = { formatCurrency, formatPercentSigned, getProfitClass, getDrawdownClass, getPerformanceClass };
  Math = Math;

  // Computed
  filteredAccounts = computed(() => {
    let result = this.accounts();
    const clientF = this.clientFilter();
    if (clientF !== 'all') {
      result = result.filter(a => a.client === clientF);
    }

    const query = this.searchQuery().toLowerCase().trim();
    if (query) {
      result = result.filter(a =>
        a.name.toLowerCase().includes(query) ||
        a.id.toString().includes(query) ||
        a.broker.toLowerCase().includes(query) ||
        (a.client && a.client.toLowerCase().includes(query))
      );
    }

    const col = this.sortColumn();
    const dir = this.sortDirection();
    result = [...result].sort((a, b) => {
      let valA: number | string, valB: number | string;
      switch (col) {
        case 'name': valA = a.name.toLowerCase(); valB = b.name.toLowerCase(); break;
        case 'balance': valA = a.balance; valB = b.balance; break;
        case 'profit': valA = a.profit; valB = b.profit; break;
        case 'profit_percent': valA = a.profit_percent; valB = b.profit_percent; break;
        case 'win_rate': valA = a.win_rate; valB = b.win_rate; break;
        case 'drawdown': valA = a.drawdown; valB = b.drawdown; break;
        case 'trades': valA = a.trades; valB = b.trades; break;
        default: valA = a.balance; valB = b.balance;
      }
      if (valA < valB) return dir === 'asc' ? -1 : 1;
      if (valA > valB) return dir === 'asc' ? 1 : -1;
      return 0;
    });

    const favs = this.storage.getFavorites();
    result = [...result].sort((a, b) => (favs.has(b.id) ? 1 : 0) - (favs.has(a.id) ? 1 : 0));
    return result;
  });

  connectedCount = computed(() => this.filteredAccounts().filter(a => a.connected).length);
  totalEUR = computed(() => this.filteredAccounts().filter(a => a.currency === 'EUR' && a.connected).reduce((s, a) => s + a.balance, 0));
  totalUSD = computed(() => this.filteredAccounts().filter(a => a.currency === 'USD' && a.connected).reduce((s, a) => s + a.balance, 0));
  totalProfitEUR = computed(() => this.filteredAccounts().filter(a => a.currency === 'EUR' && a.connected).reduce((s, a) => s + a.profit, 0));
  totalProfitUSD = computed(() => this.filteredAccounts().filter(a => a.currency === 'USD' && a.connected).reduce((s, a) => s + a.profit, 0));
  totalTrades = computed(() => this.filteredAccounts().filter(a => a.connected).reduce((s, a) => s + a.trades, 0));

  globalWinRate = computed(() => {
    const connected = this.filteredAccounts().filter(a => a.connected && a.trades > 0);
    if (!connected.length) return 0;
    const totalW = connected.reduce((s, a) => s + (a.win_rate * a.trades), 0);
    const totalT = connected.reduce((s, a) => s + a.trades, 0);
    return totalT > 0 ? totalW / totalT : 0;
  });

  globalGrowthEUR = computed(() => {
    const eur = this.filteredAccounts().filter(a => a.currency === 'EUR' && a.connected);
    if (!eur.length) return 0;
    const dep = eur.reduce((s, a) => s + (a.balance - a.profit), 0);
    const prof = eur.reduce((s, a) => s + a.profit, 0);
    return dep > 0 ? (prof / dep) * 100 : 0;
  });

  globalGrowthUSD = computed(() => {
    const usd = this.filteredAccounts().filter(a => a.currency === 'USD' && a.connected);
    if (!usd.length) return 0;
    const dep = usd.reduce((s, a) => s + (a.balance - a.profit), 0);
    const prof = usd.reduce((s, a) => s + a.profit, 0);
    return dep > 0 ? (prof / dep) * 100 : 0;
  });

  cosmosEliteCount = computed(() => this.accounts().filter(a => a.client === 'CosmosElite').length);
  akajCount = computed(() => this.accounts().filter(a => a.client === 'Akaj').length);

  constructor(
    private router: Router,
    private api: Mt5ApiService,
    public storage: StorageService
  ) {}

  ngOnInit(): void {
    this.loadAccounts();
    this.loadSparklines();
    this.loadMonthlyGrowth();
    this.startAutoRefresh();
  }

  ngOnDestroy(): void {
    this.stopAutoRefresh();
  }

  loadAccounts(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getAccounts().subscribe({
      next: (accounts) => {
        this.accounts.set(accounts);
        this.loading.set(false);
        this.lastRefreshTime.set(new Date());
        this.loadSparklines();
      },
      error: () => {
        this.error.set('Impossible de charger les comptes');
        this.loading.set(false);
      }
    });
  }

  loadSparklines(): void {
    this.api.getSparklines(100).subscribe({
      next: (data) => this.sparklines.set(data),
      error: () => {}
    });
  }

  loadMonthlyGrowth(): void {
    this.api.getGlobalMonthlyGrowth().subscribe({
      next: (data) => this.monthlyGrowth.set(data),
      error: () => {}
    });
  }

  startAutoRefresh(): void {
    if (this.autoRefreshEnabled()) {
      this.refreshSubscription = interval(this.autoRefreshInterval).subscribe(() => {
        if (this.autoRefreshEnabled()) this.loadAccounts();
      });
    }
  }

  stopAutoRefresh(): void {
    this.refreshSubscription?.unsubscribe();
  }

  toggleAutoRefresh(): void {
    this.autoRefreshEnabled.set(!this.autoRefreshEnabled());
    if (this.autoRefreshEnabled()) this.startAutoRefresh();
    else this.stopAutoRefresh();
  }

  refresh(): void { this.loadAccounts(); }
  setViewMode(mode: ViewMode): void { this.viewMode.set(mode); }
  setClientFilter(filter: ClientFilter): void { this.clientFilter.set(filter); }
  setSearchQuery(query: string): void { this.searchQuery.set(query); }

  sortBy(column: SortColumn): void {
    if (this.sortColumn() === column) {
      this.sortDirection.set(this.sortDirection() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortColumn.set(column);
      this.sortDirection.set('desc');
    }
  }

  getSortIcon(column: SortColumn): string {
    if (this.sortColumn() !== column) return 'fa-sort';
    return this.sortDirection() === 'asc' ? 'fa-sort-up' : 'fa-sort-down';
  }

  getSparklineData(accountId: number): number[] {
    return this.sparklines()[accountId] || [];
  }

  toggleFavorite(accountId: number, event: Event): void {
    event.stopPropagation();
    this.storage.toggleFavorite(accountId);
  }

  openAccount(account: AccountSummary): void {
    if (!account.connected) return;
    this.api.connectToAccount(account.id).subscribe({
      next: () => this.router.navigate(['/accounts', account.id]),
      error: () => this.error.set(`Impossible de se connecter au compte ${account.id}`)
    });
  }
}
