import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { FirmStateService } from '@app/core';
import { AccountsApiService, AccountSummary } from '@app/data-access';
import { FirmWithProfiles } from '@app/data-access/models/firm.model';
import { formatCurrency } from '@app/shared';

interface CurrencyBalance {
  currency: string;
  balance: number;
}

interface FirmSummary {
  firm: FirmWithProfiles;
  balances: CurrencyBalance[];
  connectedCount: number;
  totalCount: number;
}

function groupByCurrency(accounts: AccountSummary[]): CurrencyBalance[] {
  const map = new Map<string, number>();
  for (const a of accounts) {
    map.set(a.currency, (map.get(a.currency) ?? 0) + a.balance);
  }
  return Array.from(map.entries())
    .map(([currency, balance]) => ({ currency, balance }))
    .sort((a, b) => b.balance - a.balance);
}

@Component({
  selector: 'app-firms-dashboard',
  standalone: true,
  template: `
    <div class="dashboard-page">
      <header class="page-header">
        <h1 class="page-title"><i class="fa fa-th-large"></i> Dashboard</h1>
        <span class="count-badge">{{ firmState.firms().length }} firms</span>
      </header>

      @if (loading()) {
        <div class="loading-state">
          <i class="fa fa-spinner fa-spin"></i>
          <p>Chargement...</p>
        </div>
      }

      @if (!loading() && firmSummaries().length > 0) {
        <!-- Grand Total -->
        <section class="total-section">
          <div class="total-card">
            <div class="total-row">
              @for (b of grandTotalBalances(); track b.currency) {
                <div class="total-item">
                  <span class="total-label">Balance {{ b.currency }}</span>
                  <span class="total-value">{{ fmt.formatCurrency(b.balance, b.currency) }}</span>
                </div>
              }
              <div class="total-item">
                <span class="total-label">Comptes</span>
                <span class="total-value">{{ grandTotalCounts().connected }}/{{ grandTotalCounts().total }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Firm Cards -->
        <section class="firms-grid">
          @for (s of firmSummaries(); track s.firm.id) {
            <div class="firm-card" (click)="goToFirm(s.firm)">
              <div class="firm-card-header">
                <div class="firm-icon">
                  <i class="fa fa-building"></i>
                </div>
                <div class="firm-title">
                  <h2>{{ s.firm.name }}</h2>
                  <span class="firm-meta">{{ s.connectedCount }}/{{ s.totalCount }} comptes</span>
                </div>
                <i class="fa fa-chevron-right card-arrow"></i>
              </div>
              <div class="firm-card-body">
                @for (b of s.balances; track b.currency) {
                  <div class="stat">
                    <span class="stat-label">Balance {{ b.currency }}</span>
                    <span class="stat-value">{{ fmt.formatCurrency(b.balance, b.currency) }}</span>
                  </div>
                }
              </div>
            </div>
          }
        </section>
      }

      @if (!loading() && firmSummaries().length === 0) {
        <div class="empty-state">
          <i class="fa fa-building"></i>
          <p>Aucune firm configuree</p>
          <button class="btn-primary" (click)="goToFirms()">
            <i class="fa fa-plus"></i> Configurer les firms
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    :host {
      --accent: #2962ff;
      --bg-card: #111;
      --border-color: #1a1a1a;
      --text-primary: #fff;
      --text-secondary: #888;
      --text-muted: #555;
      --success: #00c853;
      --danger: #ff1744;
    }

    .dashboard-page {
      padding: 24px;
      max-width: 1200px;
    }

    .page-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 24px;
    }

    .page-title {
      font-size: 20px;
      font-weight: 700;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .page-title i {
      color: var(--accent);
      font-size: 18px;
    }

    .count-badge {
      font-size: 12px;
      color: var(--accent);
      background: rgba(41, 98, 255, 0.12);
      padding: 4px 10px;
      border-radius: 12px;
      font-weight: 600;
    }

    /* Loading */
    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 60px 0;
      color: var(--text-muted);
    }

    .loading-state i { font-size: 24px; }

    /* Total Section */
    .total-section { margin-bottom: 24px; }

    .total-card {
      background: linear-gradient(135deg, rgba(41, 98, 255, 0.08), rgba(41, 98, 255, 0.02));
      border: 1px solid rgba(41, 98, 255, 0.2);
      border-radius: 12px;
      padding: 20px 24px;
    }

    .total-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0;
    }

    .total-item {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      padding: 0 16px;
      border-right: 1px solid rgba(41, 98, 255, 0.15);
    }

    .total-item:last-child {
      border-right: none;
    }

    .total-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
    }

    .total-value {
      font-size: 20px;
      font-weight: 700;
      color: var(--text-primary);
    }

    /* Firms Grid */
    .firms-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 16px;
    }

    .firm-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .firm-card:hover {
      border-color: rgba(41, 98, 255, 0.3);
      transform: translateY(-2px);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    .firm-card-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }

    .firm-icon {
      width: 40px;
      height: 40px;
      min-width: 40px;
      background: rgba(41, 98, 255, 0.12);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--accent);
      font-size: 16px;
    }

    .firm-title {
      flex: 1;
    }

    .firm-title h2 {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;
    }

    .firm-meta {
      font-size: 12px;
      color: var(--text-secondary);
    }

    .card-arrow {
      color: var(--text-muted);
      font-size: 12px;
      transition: transform 0.2s ease;
    }

    .firm-card:hover .card-arrow {
      transform: translateX(4px);
      color: var(--accent);
    }

    .firm-card-body {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }

    .stat {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .stat-label {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }

    .stat-value {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }

    /* Empty State */
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      padding: 80px 0;
      color: var(--text-muted);
    }

    .empty-state i { font-size: 48px; }
    .empty-state p { font-size: 14px; }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 20px;
      background: var(--accent);
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }

    .btn-primary:hover { background: #1e88e5; }

    @media (max-width: 768px) {
      .firms-grid { grid-template-columns: 1fr; }
    }
  `]
})
export class FirmsDashboardComponent implements OnInit {
  readonly firmState = inject(FirmStateService);
  private readonly accountsApi = inject(AccountsApiService);
  private readonly router = inject(Router);

  accounts = signal<AccountSummary[]>([]);
  loading = signal(true);

  fmt = { formatCurrency };

  firmSummaries = computed<FirmSummary[]>(() => {
    const firms = this.firmState.firms();
    const accs = this.accounts();
    if (firms.length === 0) return [];

    return firms.map(firm => {
      const profileNames = firm.profiles.map(p => p.name);
      const firmAccounts = accs.filter(a => a.client !== null && profileNames.includes(a.client));
      return {
        firm,
        balances: groupByCurrency(firmAccounts),
        connectedCount: firmAccounts.filter(a => a.connected).length,
        totalCount: firmAccounts.length,
      };
    });
  });

  grandTotalBalances = computed<CurrencyBalance[]>(() => {
    const accs = this.accounts();
    const allProfileNames = this.firmState.firms().flatMap(f => f.profiles.map(p => p.name));
    const firmAccounts = accs.filter(a => a.client !== null && allProfileNames.includes(a.client));
    return groupByCurrency(firmAccounts);
  });

  grandTotalCounts = computed(() => {
    const summaries = this.firmSummaries();
    return {
      connected: summaries.reduce((sum, s) => sum + s.connectedCount, 0),
      total: summaries.reduce((sum, s) => sum + s.totalCount, 0),
    };
  });

  ngOnInit(): void {
    this.accountsApi.getAccounts().subscribe({
      next: (accounts) => {
        this.accounts.set(accounts);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  goToFirm(firm: { id: number; name: string }): void {
    this.firmState.selectFirm(firm.id);
    const slug = this.firmState.selectedFirmSlug();
    this.router.navigate([`/${slug}/accounts`]);
  }

  goToFirms(): void {
    this.router.navigate(['/firms']);
  }
}
