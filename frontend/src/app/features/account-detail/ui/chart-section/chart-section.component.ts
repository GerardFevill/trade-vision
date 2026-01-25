import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartType } from 'chart.js';
import { AccountStats } from '@app/data-access';
import { formatCurrency, formatPercent, getProfitClass } from '@app/shared';

export type ChartMode = 'all' | 'growth' | 'drawdown';
export type Timeframe = '1H' | '1D' | '1W' | '1M' | '1Y' | 'All';

@Component({
  selector: 'app-chart-section',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  templateUrl: './chart-section.component.html',
  styleUrl: './chart-section.component.scss'
})
export class ChartSectionComponent {
  stats = input<AccountStats | undefined>();
  currency = input<string>('EUR');
  activeChart = input<ChartMode>('all');
  activeTimeframe = input<Timeframe>('All');
  chartData = input<ChartConfiguration['data']>({ labels: [], datasets: [] });
  chartOptions = input<ChartConfiguration['options']>({});

  onChartChange = output<ChartMode>();
  onTimeframeChange = output<Timeframe>();

  chartType: ChartType = 'line';
  timeframes: Timeframe[] = ['1H', '1D', '1W', '1M', '1Y', 'All'];

  fmt = { formatCurrency, formatPercent, getProfitClass };
}
