import { Component, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Mt5Service, AccountSummary, SparklineData, GlobalMonthlyGrowth } from '../../services/mt5.service';
import { interval, Subscription } from 'rxjs';

type ViewMode = 'grid' | 'list';
type BrokerFilter = 'all' | 'roboforex' | 'icmarkets';
type SortColumn = 'name' | 'balance' | 'profit' | 'profit_percent' | 'win_rate' | 'drawdown' | 'trades';
type SortDirection = 'asc' | 'desc';

@Component({
  selector: 'app-accounts-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './accounts-list.component.html',
  styleUrl: './accounts-list.component.scss'
})
export class AccountsListComponent implements OnInit, OnDestroy {
  Math = Math;

  accounts = signal<AccountSummary[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  viewMode = signal<ViewMode>('grid');
  brokerFilter = signal<BrokerFilter>('all');

  // Recherche
  searchQuery = signal<string>('');

  // Tri
  sortColumn = signal<SortColumn>('balance');
  sortDirection = signal<SortDirection>('desc');

  // Favoris (stockés en localStorage)
  favorites = signal<Set<number>>(new Set());

  // Rafraîchissement auto
  autoRefreshEnabled = signal<boolean>(true);
  autoRefreshInterval = 5 * 60 * 1000; // 5 minutes
  private refreshSubscription?: Subscription;
  lastRefreshTime = signal<Date | null>(null);

  // Sparklines
  sparklines = signal<SparklineData>({});

  // Croissance mensuelle globale
  monthlyGrowth = signal<GlobalMonthlyGrowth[]>([]);
  monthNames = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'];

  // Comptes filtrés, triés et avec favoris en premier
  filteredAccounts = computed(() => {
    let result = this.accounts();

    // Filtre par broker
    const brokerF = this.brokerFilter();
    if (brokerF === 'roboforex') {
      result = result.filter(a => a.broker.toLowerCase().includes('roboforex'));
    } else if (brokerF === 'icmarkets') {
      result = result.filter(a => !a.broker.toLowerCase().includes('roboforex'));
    }

    // Filtre par recherche
    const query = this.searchQuery().toLowerCase().trim();
    if (query) {
      result = result.filter(a =>
        a.name.toLowerCase().includes(query) ||
        a.id.toString().includes(query) ||
        a.broker.toLowerCase().includes(query)
      );
    }

    // Tri
    const col = this.sortColumn();
    const dir = this.sortDirection();
    result = [...result].sort((a, b) => {
      let valA: number | string;
      let valB: number | string;

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

    // Favoris en premier
    const favs = this.favorites();
    result = [...result].sort((a, b) => {
      const aFav = favs.has(a.id) ? 1 : 0;
      const bFav = favs.has(b.id) ? 1 : 0;
      return bFav - aFav;
    });

    return result;
  });

  connectedCount = computed(() => this.accounts().filter(a => a.connected).length);

  // Totaux par devise
  totalEUR = computed(() => {
    return this.accounts()
      .filter(a => a.currency === 'EUR' && a.connected)
      .reduce((sum, a) => sum + a.balance, 0);
  });

  totalUSD = computed(() => {
    return this.accounts()
      .filter(a => a.currency === 'USD' && a.connected)
      .reduce((sum, a) => sum + a.balance, 0);
  });

  totalProfitEUR = computed(() => {
    return this.accounts()
      .filter(a => a.currency === 'EUR' && a.connected)
      .reduce((sum, a) => sum + a.profit, 0);
  });

  totalProfitUSD = computed(() => {
    return this.accounts()
      .filter(a => a.currency === 'USD' && a.connected)
      .reduce((sum, a) => sum + a.profit, 0);
  });

  // Stats globales
  totalTrades = computed(() => {
    return this.accounts()
      .filter(a => a.connected)
      .reduce((sum, a) => sum + a.trades, 0);
  });

  globalWinRate = computed(() => {
    const connected = this.accounts().filter(a => a.connected && a.trades > 0);
    if (connected.length === 0) return 0;
    const totalWeighted = connected.reduce((sum, a) => sum + (a.win_rate * a.trades), 0);
    const totalTr = connected.reduce((sum, a) => sum + a.trades, 0);
    return totalTr > 0 ? totalWeighted / totalTr : 0;
  });

  // Croissance globale pondérée
  globalGrowthEUR = computed(() => {
    const eurAccounts = this.accounts().filter(a => a.currency === 'EUR' && a.connected);
    if (eurAccounts.length === 0) return 0;
    const totalDeposit = eurAccounts.reduce((sum, a) => sum + (a.balance - a.profit), 0);
    const totalProfit = eurAccounts.reduce((sum, a) => sum + a.profit, 0);
    return totalDeposit > 0 ? (totalProfit / totalDeposit) * 100 : 0;
  });

  globalGrowthUSD = computed(() => {
    const usdAccounts = this.accounts().filter(a => a.currency === 'USD' && a.connected);
    if (usdAccounts.length === 0) return 0;
    const totalDeposit = usdAccounts.reduce((sum, a) => sum + (a.balance - a.profit), 0);
    const totalProfit = usdAccounts.reduce((sum, a) => sum + a.profit, 0);
    return totalDeposit > 0 ? (totalProfit / totalDeposit) * 100 : 0;
  });

  // Totaux par broker
  roboforexCount = computed(() =>
    this.accounts().filter(a => a.broker.toLowerCase().includes('roboforex')).length
  );

  icmarketsCount = computed(() =>
    this.accounts().filter(a => !a.broker.toLowerCase().includes('roboforex')).length
  );

  constructor(private router: Router, private mt5: Mt5Service) {}

  ngOnInit(): void {
    this.loadFavorites();
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

    this.mt5.getAccounts().subscribe({
      next: (accounts) => {
        this.accounts.set(accounts);
        this.loading.set(false);
        this.lastRefreshTime.set(new Date());
        // Recharger les sparklines aussi
        this.loadSparklines();
      },
      error: (err) => {
        console.error('Erreur chargement comptes:', err);
        this.error.set('Impossible de charger les comptes');
        this.loading.set(false);
      }
    });
  }

  loadSparklines(): void {
    this.mt5.getSparklines(20).subscribe({
      next: (data) => {
        this.sparklines.set(data);
      },
      error: (err) => {
        console.error('Erreur chargement sparklines:', err);
      }
    });
  }

  loadMonthlyGrowth(): void {
    this.mt5.getGlobalMonthlyGrowth().subscribe({
      next: (data) => {
        this.monthlyGrowth.set(data);
      },
      error: (err) => {
        console.error('Erreur chargement croissance mensuelle:', err);
      }
    });
  }

  getMonthValue(yearData: GlobalMonthlyGrowth, monthName: string): { eur: number; usd: number } | null {
    const monthData = yearData.months[monthName];
    if (!monthData) return null;
    return { eur: monthData.profit_eur, usd: monthData.profit_usd };
  }

  getSparklineData(accountId: number): number[] {
    return this.sparklines()[accountId] || [];
  }

  getSparklinePath(accountId: number): string {
    const data = this.getSparklineData(accountId);
    if (data.length < 2) return '';

    const width = 100;
    const height = 30;
    const padding = 2; // Padding to keep line visible
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min;

    const points = data.map((value, index) => {
      const x = (index / (data.length - 1)) * width;
      // If no variation, draw line in the middle; otherwise scale normally
      const y = range === 0
        ? height / 2
        : padding + ((max - value) / range) * (height - 2 * padding);
      return `${x},${y}`;
    });

    return `M ${points.join(' L ')}`;
  }

  getSparklineColor(accountId: number): string {
    const data = this.getSparklineData(accountId);
    if (data.length < 2) return '#888888';
    return data[data.length - 1] >= data[0] ? '#22c55e' : '#ef4444';
  }

  // Auto-refresh
  startAutoRefresh(): void {
    if (this.autoRefreshEnabled()) {
      this.refreshSubscription = interval(this.autoRefreshInterval).subscribe(() => {
        if (this.autoRefreshEnabled()) {
          this.loadAccounts();
        }
      });
    }
  }

  stopAutoRefresh(): void {
    this.refreshSubscription?.unsubscribe();
  }

  toggleAutoRefresh(): void {
    this.autoRefreshEnabled.set(!this.autoRefreshEnabled());
    if (this.autoRefreshEnabled()) {
      this.startAutoRefresh();
    } else {
      this.stopAutoRefresh();
    }
  }

  // Favoris
  loadFavorites(): void {
    try {
      const stored = localStorage.getItem('mt5_favorites');
      if (stored) {
        const ids = JSON.parse(stored) as number[];
        this.favorites.set(new Set(ids));
      }
    } catch (e) {
      console.error('Erreur chargement favoris:', e);
    }
  }

  saveFavorites(): void {
    try {
      const ids = Array.from(this.favorites());
      localStorage.setItem('mt5_favorites', JSON.stringify(ids));
    } catch (e) {
      console.error('Erreur sauvegarde favoris:', e);
    }
  }

  toggleFavorite(accountId: number, event: Event): void {
    event.stopPropagation();
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

  // Tri
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

  openAccount(account: AccountSummary): void {
    if (!account.connected) {
      return;
    }
    this.mt5.connectToAccount(account.id).subscribe({
      next: () => {
        this.router.navigate(['/dashboard', account.id]);
      },
      error: (err) => {
        console.error('Erreur connexion compte:', err);
        this.error.set(`Impossible de se connecter au compte ${account.id}`);
      }
    });
  }

  refresh(): void {
    this.loadAccounts();
  }

  setViewMode(mode: ViewMode): void {
    this.viewMode.set(mode);
  }

  setBrokerFilter(filter: BrokerFilter): void {
    this.brokerFilter.set(filter);
  }

  // Classes de performance
  getPerformanceClass(account: AccountSummary): string {
    if (account.profit_percent >= 50) return 'perf-excellent';
    if (account.profit_percent >= 20) return 'perf-good';
    if (account.profit_percent >= 0) return 'perf-neutral';
    if (account.profit_percent >= -20) return 'perf-warning';
    return 'perf-danger';
  }

  getProfitClass(value: number): string {
    return value >= 0 ? 'positive' : 'negative';
  }

  getDrawdownClass(value: number): string {
    if (value >= 30) return 'dd-critical';
    if (value >= 20) return 'dd-warning';
    if (value >= 10) return 'dd-moderate';
    return 'dd-low';
  }

  formatCurrency(value: number, currency: string): string {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency }).format(value);
  }

  formatPercent(value: number): string {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  }

  formatTime(date: Date | null): string {
    if (!date) return '-';
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }
}
