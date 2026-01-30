import { Component, Input, Output, EventEmitter, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { Mt5ApiService } from '@app/data-access';
import { MonthlySnapshot, MonthlyAccountRecord, CurrentMonthPreview, WITHDRAWAL_PERCENTAGES } from '@app/data-access/models/portfolio.model';
import { formatCurrency } from '@app/shared';

@Component({
  selector: 'app-monthly-records',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './monthly-records.component.html',
  styleUrl: './monthly-records.component.scss'
})
export class MonthlyRecordsComponent implements OnInit {
  @Input({ required: true }) portfolioId!: number;
  @Input({ required: true }) portfolioType!: string;
  @Output() close = new EventEmitter<void>();

  months = signal<string[]>([]);
  selectedMonth = signal<string>('');
  snapshot = signal<MonthlySnapshot | null>(null);
  currentPreview = signal<CurrentMonthPreview | null>(null);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  editMode = signal<boolean>(false);
  withdrawalEdits = signal<Map<number, number>>(new Map());

  fmt = { formatCurrency };

  withdrawalPct = computed(() => WITHDRAWAL_PERCENTAGES[this.portfolioType] || 80);

  currentMonth = computed(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });

  constructor(private api: Mt5ApiService) {}

  ngOnInit(): void {
    this.loadMonthlyHistory();
  }

  loadMonthlyHistory(): void {
    this.loading.set(true);
    this.api.getMonthlyHistory(this.portfolioId).subscribe({
      next: (res) => {
        this.months.set(res.months);
        this.loading.set(false);
        // Load current month preview by default
        this.loadCurrentPreview();
      },
      error: () => {
        this.loading.set(false);
        this.loadCurrentPreview();
      }
    });
  }

  loadCurrentPreview(): void {
    this.loading.set(true);
    this.selectedMonth.set('');
    this.snapshot.set(null);

    this.api.getCurrentMonthPreview(this.portfolioId).subscribe({
      next: (preview) => {
        this.currentPreview.set(preview);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Erreur lors du chargement');
        this.loading.set(false);
      }
    });
  }

  loadMonth(month: string): void {
    this.loading.set(true);
    this.selectedMonth.set(month);
    this.currentPreview.set(null);
    this.editMode.set(false);

    this.api.getMonthlySnapshot(this.portfolioId, month).subscribe({
      next: (snap) => {
        this.snapshot.set(snap);
        this.loading.set(false);
        // Initialize withdrawal edits
        const edits = new Map<number, number>();
        snap.accounts.forEach(a => edits.set(a.account_id, a.actual_withdrawal));
        this.withdrawalEdits.set(edits);
      },
      error: () => {
        this.error.set('Erreur lors du chargement du mois');
        this.loading.set(false);
      }
    });
  }

  toggleEditMode(): void {
    this.editMode.update(v => !v);
  }

  updateWithdrawal(accountId: number, value: number): void {
    const edits = new Map(this.withdrawalEdits());
    edits.set(accountId, value);
    this.withdrawalEdits.set(edits);
  }

  applySuggested(): void {
    const snap = this.snapshot();
    if (!snap) return;

    const edits = new Map<number, number>();
    snap.accounts.forEach(a => edits.set(a.account_id, a.suggested_withdrawal));
    this.withdrawalEdits.set(edits);
  }

  saveWithdrawals(): void {
    const month = this.selectedMonth();
    if (!month) return;

    const edits = this.withdrawalEdits();
    const withdrawals = Array.from(edits.entries()).map(([account_id, withdrawal]) => ({
      account_id,
      withdrawal
    }));

    this.loading.set(true);
    this.api.updateMonthlyWithdrawals(this.portfolioId, month, withdrawals).subscribe({
      next: () => {
        this.editMode.set(false);
        this.loadMonth(month);
      },
      error: () => {
        this.error.set('Erreur lors de la sauvegarde');
        this.loading.set(false);
      }
    });
  }

  formatMonth(month: string): string {
    const [year, m] = month.split('-');
    const months = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aou', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[parseInt(m) - 1]} ${year}`;
  }

  getProfitClass(value: number): string {
    return value >= 0 ? 'positive' : 'negative';
  }

  onClose(): void {
    this.close.emit();
  }
}
