import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AccountInfo, AccountStats, TradeStats } from '@app/data-access';
import { formatCurrency, formatPercent, formatDate, formatTime, getProfitClass } from '@app/shared';

@Component({
  selector: 'app-account-detail-sidebar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class AccountDetailSidebarComponent {
  account = input<AccountInfo | undefined>();
  stats = input<AccountStats | undefined>();
  tradeStats = input<TradeStats | undefined>();
  currency = input<string>('EUR');
  isConnected = input<boolean>(false);
  loading = input<boolean>(false);
  lastUpdate = input<Date | null>(null);

  onBack = output<void>();
  onRefresh = output<void>();

  // Template helpers
  fmt = { formatCurrency, formatPercent, formatDate, formatTime, getProfitClass };
}
