import { Component, OnInit, computed, effect, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartType } from 'chart.js';

import { Mt5ApiService, HistoryPoint, DailyDrawdown } from '@app/data-access';
import { SparklineComponent } from '@app/shared';

import {
  Chart, LineController, LineElement, PointElement,
  LinearScale, CategoryScale, Filler, Tooltip, Legend,
  RadarController, RadialLinearScale
} from 'chart.js';

Chart.register(
  LineController, LineElement, PointElement, LinearScale, CategoryScale,
  Filler, Tooltip, Legend, RadarController, RadialLinearScale
);

type TabType = 'account' | 'history' | 'statistics' | 'risks';
type ChartMode = 'all' | 'growth' | 'drawdown';
type MonthlyDisplayMode = 'percent' | 'value';
type Timeframe = '1H' | '1D' | '1W' | '1M' | '1Y' | 'All';

@Component({
  selector: 'app-account-detail-page',
  standalone: true,
  imports: [CommonModule, BaseChartDirective, SparklineComponent],
  templateUrl: './account-detail-page.component.html',
  styleUrl: './account-detail-page.component.scss'
})
export class AccountDetailPageComponent implements OnInit {
  // UI State
  activeTab = signal<TabType>('account');
  activeChart = signal<ChartMode>('all');
  monthlyDisplayMode = signal<MonthlyDisplayMode>('percent');
  activeTimeframe = signal<Timeframe>('All');

  // Constants
  timeframes: Timeframe[] = ['1H', '1D', '1W', '1M', '1Y', 'All'];
  monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  // Computed from service
  loading = computed(() => this.api.loading());
  lastUpdate = computed(() => this.api.lastUpdate());
  dashboard = computed(() => this.api.dashboard());
  account = computed(() => this.dashboard()?.account);
  stats = computed(() => this.dashboard()?.stats);
  tradeStats = computed(() => this.dashboard()?.trade_stats);
  risk = computed(() => this.dashboard()?.risk_metrics);
  positions = computed(() => this.dashboard()?.open_positions || []);
  monthlyGrowth = computed(() => this.dashboard()?.monthly_growth || []);
  trades = computed(() => this.api.trades());
  status = computed(() => this.api.connectionStatus());
  error = computed(() => this.api.error());
  isConnected = computed(() => this.status()?.connected ?? false);
  currency = computed(() => this.account()?.currency || 'EUR');
  dailyDrawdown = computed(() => this.api.dailyDrawdown());
  sparklineData = computed(() => this.api.sparkline());

  totalGrowth = computed(() => {
    const data = this.monthlyGrowth();
    if (!data.length) return null;
    return data.reduce((sum, year) => sum + (year.year_total ?? 0), 0);
  });

  totalValue = computed(() => {
    const data = this.monthlyGrowth();
    if (!data.length) return null;
    return data.reduce((sum, year) => sum + (year.year_total_value ?? 0), 0);
  });

  // Main Chart
  chartType: ChartType = 'line';
  chartData: ChartConfiguration['data'] = { labels: [], datasets: [] };
  chartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: {
      legend: { display: true, position: 'top', labels: { color: '#888', font: { size: 11 } } },
      tooltip: { backgroundColor: '#1a1a1a', titleColor: '#fff', bodyColor: '#aaa', borderColor: '#333', borderWidth: 1 }
    },
    scales: {
      x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 10 } },
      y: { type: 'linear', position: 'left', grid: { color: '#1f1f1f' }, ticks: { color: '#22c55e', font: { size: 10 } } },
      y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#f59e0b', font: { size: 10 } }, reverse: true }
    }
  };

  // Radar Chart
  radarData: ChartConfiguration<'radar'>['data'] = {
    labels: ['Algo trading', 'Bénéfice trades', 'Perte trades', 'Activité', 'Charge dépôt', 'Prélèvement max'],
    datasets: [{ data: [0, 0, 0, 0, 0, 0], backgroundColor: 'rgba(59, 130, 246, 0.2)', borderColor: '#3b82f6', borderWidth: 2, pointBackgroundColor: '#3b82f6' }]
  };

  radarOptions: ChartConfiguration<'radar'>['options'] = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: { legend: { display: false } },
    scales: {
      r: {
        angleLines: { color: '#2a2a2a' },
        grid: { color: '#2a2a2a' },
        pointLabels: { color: '#888', font: { size: 10 } },
        ticks: { display: false, stepSize: 20 },
        min: 0,
        max: 100
      }
    }
  };

  // Drawdown Chart
  drawdownChartData: ChartConfiguration['data'] = { labels: [], datasets: [] };
  drawdownChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: '#1a1a1a', titleColor: '#fff', bodyColor: '#aaa', borderColor: '#333', borderWidth: 1 }
    },
    scales: {
      x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 12 } },
      y: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 } }, reverse: true }
    }
  };

  constructor(
    private api: Mt5ApiService,
    private router: Router
  ) {
    effect(() => {
      const history = this.api.history();
      this.activeTimeframe();
      this.activeChart();
      if (history.length) this.updateChart(history);
    });

    effect(() => {
      const ts = this.tradeStats();
      const r = this.risk();
      if (ts && r) this.updateRadar();
    });

    effect(() => {
      const daily = this.api.dailyDrawdown();
      this.updateDrawdownChart(daily);
    });
  }

  ngOnInit(): void {
    this.api.startPolling();
  }

  goBack(): void {
    this.router.navigate(['/accounts']);
  }

  setTab(tab: TabType): void {
    this.activeTab.set(tab);
  }

  setChart(mode: ChartMode): void {
    this.activeChart.set(mode);
  }

  setTimeframe(tf: Timeframe): void {
    this.activeTimeframe.set(tf);
  }

  setMonthlyDisplay(mode: MonthlyDisplayMode): void {
    this.monthlyDisplayMode.set(mode);
  }

  refresh(): void {
    this.api.refresh();
  }

  resetDrawdown(): void {
    this.api.resetDrawdown().subscribe();
  }

  // Formatters
  fmt(val: number | null | undefined, decimals = 2): string {
    return val != null ? val.toFixed(decimals) : '-';
  }

  fmtCurrency(val: number | null | undefined): string {
    if (val == null) return '-';
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: this.currency() }).format(val);
  }

  fmtPct(val: number | null | undefined): string {
    return val != null ? val.toFixed(2) + '%' : '-';
  }

  fmtTime(seconds: number | null | undefined): string {
    if (!seconds) return '-';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  }

  fmtDate(date: string | null | undefined): string {
    if (!date) return '-';
    return new Date(date).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  getProfitClass(val: number | null | undefined): string {
    if (val == null) return '';
    return val >= 0 ? 'positive' : 'negative';
  }

  getDrawdownClass(val: number | null | undefined): string {
    if (val == null) return '';
    if (val >= 50) return 'dd-critical';
    if (val >= 30) return 'dd-warning';
    if (val >= 10) return 'dd-moderate';
    return 'dd-low';
  }

  getBarPercent(value: number | null | undefined, max: number | null | undefined): number {
    if (!value || !max || max === 0) return 0;
    return Math.min(Math.max((value / max) * 100, 0), 100);
  }

  private getTimeframeMinutes(tf: Timeframe): number {
    const map: Record<Timeframe, number> = {
      '1H': 60, '1D': 1440, '1W': 10080, '1M': 43200, '1Y': 525600, 'All': Infinity
    };
    return map[tf];
  }

  private filterHistoryByTimeframe(history: HistoryPoint[]): HistoryPoint[] {
    const tf = this.activeTimeframe();
    if (tf === 'All') return history;

    const minutes = this.getTimeframeMinutes(tf);
    const cutoff = new Date(Date.now() - minutes * 60 * 1000);
    const filtered = history.filter(h => new Date(h.timestamp) >= cutoff);
    return filtered.length === 0 ? history : filtered;
  }

  private updateChart(history: HistoryPoint[]): void {
    if (!history.length) return;

    const filtered = this.filterHistoryByTimeframe(history);
    if (!filtered.length) return;

    const tf = this.activeTimeframe();
    const formatOptions: Intl.DateTimeFormatOptions =
      tf === '1H' ? { hour: '2-digit', minute: '2-digit' }
      : tf === '1D' || tf === '1W' ? { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }
      : { day: '2-digit', month: '2-digit', year: '2-digit' };

    const labels = filtered.map(h => new Date(h.timestamp).toLocaleString('fr-FR', formatOptions));
    const mode = this.activeChart();

    if (mode === 'all') {
      this.chartOptions = {
        ...this.chartOptions,
        scales: {
          x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 10 } },
          y: { type: 'linear', position: 'left', grid: { color: '#1f1f1f' }, ticks: { color: '#22c55e', font: { size: 10 } } },
          y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#f59e0b', font: { size: 10 } }, reverse: true }
        }
      };
      this.chartData = {
        labels,
        datasets: [
          { label: 'Solde', data: filtered.map(h => h.balance), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2, yAxisID: 'y' },
          { label: 'Prélèvement %', data: filtered.map(h => h.drawdown_percent), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2, yAxisID: 'y1' }
        ]
      };
    } else if (mode === 'growth') {
      this.chartOptions = {
        ...this.chartOptions,
        scales: {
          x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 10 } },
          y: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 } } }
        }
      };
      this.chartData = {
        labels,
        datasets: [
          { label: 'Solde', data: filtered.map(h => h.balance), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 },
          { label: 'Fonds propres', data: filtered.map(h => h.equity), borderColor: '#3b82f6', backgroundColor: 'transparent', fill: false, tension: 0.3, pointRadius: 0, borderWidth: 2 }
        ]
      };
    } else {
      this.chartOptions = {
        ...this.chartOptions,
        scales: {
          x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 10 } },
          y: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 } }, reverse: true }
        }
      };
      this.chartData = {
        labels,
        datasets: [{ label: 'Prélèvement', data: filtered.map(h => h.drawdown_percent), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 }]
      };
    }
  }

  private updateRadar(): void {
    const ts = this.tradeStats();
    const r = this.risk();
    if (!ts || !r) return;

    this.radarData = {
      labels: ['Algo trading', 'Bénéfice trades', 'Perte trades', 'Activité', 'Charge dépôt', 'Prélèvement max'],
      datasets: [{
        data: [98, Math.min(ts.win_rate, 100), 100 - Math.min(ts.win_rate, 100), Math.min((ts.total_trades / 500) * 100, 100), Math.min(r.max_deposit_load, 100), Math.min(r.max_drawdown_percent, 100)],
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        borderColor: '#3b82f6',
        borderWidth: 2,
        pointBackgroundColor: '#3b82f6'
      }]
    };
  }

  private updateDrawdownChart(daily: DailyDrawdown[]): void {
    if (!daily.length) return;

    this.drawdownChartData = {
      labels: daily.map(d => d.date),
      datasets: [{
        label: 'Drawdown %',
        data: daily.map(d => d.drawdown_percent),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.2)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 2
      }]
    };
  }
}
