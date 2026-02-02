import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

import { PortfolioSummary, PORTFOLIO_TYPES } from '@app/data-access/models/portfolio.model';
import { formatCurrency, formatPercentSigned, getProfitClass } from '@app/shared';

@Component({
  selector: 'app-portfolio-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './portfolio-card.component.html',
  styleUrl: './portfolio-card.component.scss'
})
export class PortfolioCardComponent {
  @Input({ required: true }) portfolio!: PortfolioSummary;
  @Output() delete = new EventEmitter<Event>();

  fmt = { formatCurrency, formatPercentSigned, getProfitClass };

  getTypeClass(): string {
    switch (this.portfolio.type) {
      case 'Securise': return 'type-securise';
      case 'Conservateur': return 'type-conservateur';
      case 'Modere': return 'type-modere';
      case 'Agressif': return 'type-agressif';
      default: return '';
    }
  }

  getTypeIcon(): string {
    switch (this.portfolio.type) {
      case 'Securise': return 'fa-lock';
      case 'Conservateur': return 'fa-shield-alt';
      case 'Modere': return 'fa-balance-scale';
      case 'Agressif': return 'fa-bolt';
      default: return 'fa-folder';
    }
  }

  getAvailableFactors(): number[] {
    return PORTFOLIO_TYPES[this.portfolio.type as keyof typeof PORTFOLIO_TYPES] || [];
  }

  onDelete(event: Event): void {
    this.delete.emit(event);
  }
}
