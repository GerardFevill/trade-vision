import { Component, signal, computed, OnInit, OnDestroy, effect, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { interval, Subscription } from 'rxjs';

import { AccountsApiService, AnalyticsApiService, AccountSummary, SparklineData, GlobalMonthlyGrowth } from '@app/data-access';
import { StorageService, FirmStateService } from '@app/core';
import { SparklineComponent, formatCurrency, formatPercentSigned, getProfitClass, getDrawdownClass, getPerformanceClass } from '@app/shared';
type ViewMode = 'grid' | 'list';
type ClientFilter = 'all' | string;
type SortColumn = 'name' | 'balance' | 'profit' | 'profit_percent' | 'win_rate' | 'drawdown';

/**
 * Accounts Page - Smart/Container component
 * Handles data fetching and state management for accounts list
 */
@Component({
  selector: 'app-accounts-page',
  standalone: true,
  imports: [
    CommonModule,
    SparklineComponent
  ],
  templateUrl: './accounts-page.component.html',
  styleUrl: './accounts-page.component.scss'
})
export class AccountsPageComponent implements OnInit, OnDestroy {
  private readonly firmState = inject(FirmStateService);

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

  // Dynamic profiles from FirmStateService
  profiles = computed(() => this.firmState.profileNames());

  profileCounts = computed(() => {
    const counts: Record<string, number> = {};
    for (const name of this.profiles()) {
      counts[name] = this.accounts().filter(a => a.client === name).length;
    }
    return counts;
  });

  // Computed
  filteredAccounts = computed(() => {
    let result = this.accounts();
    const clientF = this.clientFilter();
    const profileList = this.profiles();
    const hasFirm = this.firmState.selectedFirmId() !== null;

    if (clientF !== 'all') {
      result = result.filter(a => a.client === clientF);
    } else if (hasFirm) {
      // Always filter by firm profiles, even if list is empty (shows 0 accounts)
      result = result.filter(a => profileList.includes(a.client || ''));
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
  totalEquityEUR = computed(() => this.filteredAccounts().filter(a => a.currency === 'EUR' && a.connected).reduce((s, a) => s + a.equity, 0));
  totalEquityUSD = computed(() => this.filteredAccounts().filter(a => a.currency === 'USD' && a.connected).reduce((s, a) => s + a.equity, 0));

  constructor(
    private router: Router,
    private accountsApi: AccountsApiService,
    private analyticsApi: AnalyticsApiService,
    public storage: StorageService
  ) {
    // Reset filter when firm changes
    effect(() => {
      this.firmState.selectedFirmId();
      this.clientFilter.set('all');
    });
  }

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
    this.accountsApi.getAccounts().subscribe({
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
    this.analyticsApi.getSparklines(100).subscribe({
      next: (data) => this.sparklines.set(data),
      error: () => {}
    });
  }

  loadMonthlyGrowth(): void {
    this.analyticsApi.getGlobalMonthlyGrowth().subscribe({
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

  // Sync from MT5 (force refresh from MetaTrader)
  syncing = signal<boolean>(false);

  syncFromMT5(): void {
    this.syncing.set(true);
    // Get accounts directly from MT5 (synchronous, bypasses cache)
    this.accountsApi.getAccounts(true).subscribe({
      next: (accounts) => {
        this.accounts.set(accounts);
        this.lastRefreshTime.set(new Date());
        this.syncing.set(false);
        this.loadSparklines();
      },
      error: () => {
        this.syncing.set(false);
      }
    });
  }

  setViewMode(mode: ViewMode): void { this.viewMode.set(mode); }
  setClientFilter(filter: string): void { this.clientFilter.set(filter); }
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
    this.accountsApi.connectToAccount(account.id).subscribe({
      next: () => {
        const slug = this.firmState.selectedFirmSlug();
        this.router.navigate([`/${slug}/accounts`, account.id]);
      },
      error: () => this.error.set(`Impossible de se connecter au compte ${account.id}`)
    });
  }
}
