import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-accounts-header',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class AccountsHeaderComponent {
  totalAccounts = input<number>(0);
  connectedCount = input<number>(0);
  loading = input<boolean>(false);

  onRefresh = output<void>();
}
