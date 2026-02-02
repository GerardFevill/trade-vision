import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule, KeyValuePipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { Mt5ApiService, AccountSummary } from '@app/data-access';
import { PortfolioDetail, PortfolioAccountDetail, CurrentMonthPreview } from '@app/data-access/models/portfolio.model';
import { formatCurrency, formatPercentSigned, getProfitClass, getDrawdownClass } from '@app/shared';
import { AccountSelectorComponent } from '../../ui/account-selector/account-selector.component';

@Component({
  selector: 'app-portfolio-detail-page',
  standalone: true,
  imports: [CommonModule, RouterLink, AccountSelectorComponent],
  templateUrl: './portfolio-detail-page.component.html',
  styleUrl: './portfolio-detail-page.component.scss'
})
export class PortfolioDetailPageComponent implements OnInit {
  portfolio = signal<PortfolioDetail | null>(null);
  availableAccounts = signal<AccountSummary[]>([]);
  allUsedAccountIds = signal<Set<number>>(new Set());
  monthlyPreview = signal<CurrentMonthPreview | null>(null);
  monthlyHistory = signal<string[]>([]);
  selectedHistoryMonth = signal<string | null>(null);
  historyData = signal<any | null>(null);
  loading = signal<boolean>(false);
  closingMonth = signal<boolean>(false);
  error = signal<string | null>(null);
  showAccountSelector = signal<boolean>(false);
  selectedFactor = signal<number | null>(null);
  editingStartingBalance = signal<number | null>(null);

  fmt = { formatCurrency, formatPercentSigned, getProfitClass, getDrawdownClass };

  // Group accounts by factor
  accountsByFactor = computed(() => {
    const p = this.portfolio();
    if (!p) return new Map<number, PortfolioAccountDetail[]>();

    const grouped = new Map<number, PortfolioAccountDetail[]>();
    for (const factor of p.available_factors) {
      grouped.set(factor, p.accounts.filter(a => a.lot_factor === factor));
    }
    return grouped;
  });

  // Group accounts by currency (for Securise portfolios)
  accountsByCurrency = computed(() => {
    const p = this.portfolio();
    if (!p) return new Map<string, PortfolioAccountDetail[]>();

    const grouped = new Map<string, PortfolioAccountDetail[]>();
    for (const acc of p.accounts) {
      const currency = acc.account?.currency || 'EUR';
      if (!grouped.has(currency)) {
        grouped.set(currency, []);
      }
      grouped.get(currency)!.push(acc);
    }
    return grouped;
  });

  // Get totals by currency
  totalsByCurrency = computed(() => {
    const p = this.portfolio();
    if (!p) return [];

    const totals = new Map<string, { balance: number; profit: number }>();
    for (const acc of p.accounts) {
      if (acc.account) {
        const currency = acc.account.currency || 'EUR';
        if (!totals.has(currency)) {
          totals.set(currency, { balance: 0, profit: 0 });
        }
        const t = totals.get(currency)!;
        t.balance += acc.account.balance || 0;
        t.profit += acc.account.profit || 0;
      }
    }
    return Array.from(totals.entries()).map(([currency, data]) => ({
      currency,
      balance: data.balance,
      profit: data.profit
    }));
  });

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: Mt5ApiService
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadPortfolio(+id);
      this.loadAvailableAccounts();
    }
  }

  loadPortfolio(id: number): void {
    this.loading.set(true);
    this.error.set(null);

    this.api.getPortfolio(id).subscribe({
      next: (portfolio) => {
        this.portfolio.set(portfolio);
        this.loading.set(false);
        this.loadMonthlyPreview(id);
        this.loadMonthlyHistory(id);
      },
      error: () => {
        this.error.set('Impossible de charger le portefeuille');
        this.loading.set(false);
      }
    });
  }

  loadMonthlyPreview(id: number): void {
    this.api.getCurrentMonthPreview(id).subscribe({
      next: (preview) => this.monthlyPreview.set(preview),
      error: () => {} // Silently fail if no monthly data
    });
  }

  loadAvailableAccounts(): void {
    this.api.getAccounts().subscribe({
      next: (accounts) => this.availableAccounts.set(accounts),
      error: () => {}
    });
    this.api.getUsedAccountIds().subscribe({
      next: (ids) => this.allUsedAccountIds.set(new Set(ids)),
      error: () => {}
    });
  }

  openAccountSelector(factor: number): void {
    this.selectedFactor.set(factor);
    this.showAccountSelector.set(true);
  }

  closeAccountSelector(): void {
    this.showAccountSelector.set(false);
    this.selectedFactor.set(null);
  }

  onAccountSelected(accountId: number): void {
    const p = this.portfolio();
    const factor = this.selectedFactor();
    if (!p || !factor) return;

    this.api.addAccountToPortfolio(p.id, { account_id: accountId, lot_factor: factor }).subscribe({
      next: () => {
        this.closeAccountSelector();
        this.loadPortfolio(p.id);
        this.loadAvailableAccounts(); // Refresh used accounts list
      },
      error: (err) => {
        this.error.set(err.error?.detail || 'Erreur lors de l\'ajout du compte');
      }
    });
  }

  removeAccount(accountId: number, event: Event): void {
    event.stopPropagation();
    const p = this.portfolio();
    if (!p) return;

    if (!confirm('Retirer ce compte du portefeuille ?')) return;

    this.api.removeAccountFromPortfolio(p.id, accountId).subscribe({
      next: () => {
        this.loadPortfolio(p.id);
        this.loadAvailableAccounts(); // Refresh used accounts list
      },
      error: () => this.error.set('Erreur lors du retrait du compte')
    });
  }

  getTypeClass(): string {
    const p = this.portfolio();
    if (!p) return '';
    switch (p.type) {
      case 'Securise': return 'type-securise';
      case 'Conservateur': return 'type-conservateur';
      case 'Modere': return 'type-modere';
      case 'Agressif': return 'type-agressif';
      default: return '';
    }
  }

  getTypeIcon(): string {
    const p = this.portfolio();
    if (!p) return 'fa-folder';
    switch (p.type) {
      case 'Securise': return 'fa-lock';
      case 'Conservateur': return 'fa-shield-alt';
      case 'Modere': return 'fa-balance-scale';
      case 'Agressif': return 'fa-bolt';
      default: return 'fa-folder';
    }
  }

  getUsedAccountIds(): Set<number> {
    return this.allUsedAccountIds();
  }

  formatMonth(month: string): string {
    const [year, m] = month.split('-');
    const months = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aou', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[parseInt(m) - 1]} ${year}`;
  }

  // Starting balance editing
  startEditBalance(accountId: number): void {
    this.editingStartingBalance.set(accountId);
  }

  cancelEdit(): void {
    this.editingStartingBalance.set(null);
  }

  toggleEditMode(): void {
    // Toggle edit mode (could show all inputs at once)
    this.editingStartingBalance.set(null);
  }

  saveStartingBalance(accountId: number, value: string): void {
    const p = this.portfolio();
    if (!p) return;

    const balance = parseFloat(value);
    if (isNaN(balance) || balance < 0) {
      this.error.set('Balance invalide');
      return;
    }

    this.api.updateStartingBalance(p.id, accountId, balance).subscribe({
      next: () => {
        this.editingStartingBalance.set(null);
        this.loadMonthlyPreview(p.id);
      },
      error: () => {
        this.error.set('Erreur lors de la mise a jour');
      }
    });
  }

  // Close current month (save Elite data)
  closeCurrentMonth(): void {
    const p = this.portfolio();
    const preview = this.monthlyPreview();
    if (!p || !preview) return;

    const confirmMsg = preview.is_elite
      ? `Cloturer le mois ${this.formatMonth(preview.month)} ?\n\nCela va sauvegarder:\n- Remuneration: ${this.fmt.formatCurrency(preview.total_remuneration || 0, 'EUR')}\n- Compound: ${this.fmt.formatCurrency(preview.total_compound || 0, 'EUR')}\n- Transferts: ${this.fmt.formatCurrency(preview.total_transfer || 0, 'EUR')}`
      : `Cloturer le mois ${this.formatMonth(preview.month)} ?`;

    if (!confirm(confirmMsg)) return;

    this.closingMonth.set(true);
    this.api.closeCurrentMonth(p.id).subscribe({
      next: (result) => {
        this.closingMonth.set(false);
        this.loadMonthlyHistory(p.id);
        alert(`Mois cloture avec succes!\n${result.accounts_closed} comptes enregistres.`);
      },
      error: (err) => {
        this.closingMonth.set(false);
        this.error.set(err.error?.detail || 'Erreur lors de la cloture');
      }
    });
  }

  // Load monthly history
  loadMonthlyHistory(portfolioId: number): void {
    this.api.getMonthlyHistory(portfolioId).subscribe({
      next: (result) => this.monthlyHistory.set(result.months || []),
      error: () => {}
    });
  }

  // View historical month (toggle)
  viewHistoryMonth(month: string): void {
    const p = this.portfolio();
    if (!p) return;

    // Toggle: if same month is clicked, collapse it
    if (this.selectedHistoryMonth() === month) {
      this.selectedHistoryMonth.set(null);
      this.historyData.set(null);
      return;
    }

    this.selectedHistoryMonth.set(month);

    if (p.type === 'Conservateur') {
      this.api.getEliteMonthlyHistory(p.id, month).subscribe({
        next: (data) => this.historyData.set(data),
        error: () => this.error.set('Erreur chargement historique')
      });
    } else {
      this.api.getMonthlySnapshot(p.id, month).subscribe({
        next: (data) => this.historyData.set(data),
        error: () => this.error.set('Erreur chargement historique')
      });
    }
  }

  closeHistory(): void {
    this.selectedHistoryMonth.set(null);
    this.historyData.set(null);
  }

  getDistributionPct(history: any, type: string): number {
    const total = (history.total_remuneration || 0) + (history.total_compound || 0) + (history.total_transfer || 0);
    if (total === 0) return 0;
    switch (type) {
      case 'remun': return (history.total_remuneration / total) * 100;
      case 'compound': return (history.total_compound / total) * 100;
      case 'transfer': return (history.total_transfer / total) * 100;
      default: return 0;
    }
  }

  getCurrencyTotal(currency: string): number {
    const totals = this.totalsByCurrency();
    const found = totals.find(t => t.currency === currency);
    return found?.balance || 0;
  }
}
