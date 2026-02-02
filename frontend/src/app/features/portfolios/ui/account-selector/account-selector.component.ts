import { Component, Input, Output, EventEmitter, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AccountSummary } from '@app/data-access';
import { formatCurrency } from '@app/shared';

@Component({
  selector: 'app-account-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './account-selector.component.html',
  styleUrl: './account-selector.component.scss'
})
export class AccountSelectorComponent {
  @Input({ required: true }) accounts: AccountSummary[] = [];
  @Input({ required: true }) usedAccountIds = new Set<number>();
  @Input({ required: true }) selectedFactor = 0;
  @Input() portfolioClient: string = ''; // Filter accounts by client
  @Output() selected = new EventEmitter<number>();
  @Output() cancel = new EventEmitter<void>();

  searchQuery = signal<string>('');
  fmt = { formatCurrency };

  filteredAccounts = computed(() => {
    const query = this.searchQuery().toLowerCase().trim();
    let result = this.accounts.filter(a => !this.usedAccountIds.has(a.id) && a.connected);

    // Filter by client if specified
    if (this.portfolioClient) {
      result = result.filter(a => a.client === this.portfolioClient);
    }

    if (query) {
      result = result.filter(a =>
        a.name.toLowerCase().includes(query) ||
        a.id.toString().includes(query)
      );
    }

    return result;
  });

  selectAccount(account: AccountSummary): void {
    this.selected.emit(account.id);
  }

  onCancel(): void {
    this.cancel.emit();
  }
}
