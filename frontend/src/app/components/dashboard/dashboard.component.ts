import { Component, OnInit, computed, effect, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartType } from 'chart.js';
import { Mt5Service, HistoryPoint, DailyDrawdown, WeeklyDrawdown, MonthlyDrawdown, YearlyDrawdown } from '../../services/mt5.service';

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
type ChartMode = 'growth' | 'drawdown';
type MonthlyDisplayMode = 'percent' | 'value';
type Timeframe = '1H' | '1D' | '1W' | '1M' | '1Y' | 'All';
type DrawdownPeriod = 'day' | 'week' | 'month' | 'year';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  activeTab = signal<TabType>('account');
  activeChart = signal<ChartMode>('growth');
  monthlyDisplayMode = signal<MonthlyDisplayMode>('percent');
  activeTimeframe = signal<Timeframe>('1D');
  activeDrawdownPeriod = signal<DrawdownPeriod>('month');

  timeframes: Timeframe[] = ['1H', '1D', '1W', '1M', '1Y', 'All'];
  drawdownPeriods: DrawdownPeriod[] = ['day', 'week', 'month', 'year'];
  drawdownPeriodLabels: Record<DrawdownPeriod, string> = {
    day: 'Jour',
    week: 'Semaine',
    month: 'Mois',
    year: 'Année'
  };

  loading = computed(() => this.mt5.loading());
  lastUpdate = computed(() => this.mt5.lastUpdate());

  constructor(public mt5: Mt5Service) {
    // Update chart when history OR timeframe OR chartMode changes
    effect(() => {
      const history = this.mt5.history();
      const tf = this.activeTimeframe(); // React to timeframe changes
      const mode = this.activeChart(); // React to chart mode changes
      if (history.length) this.updateChart(history);
    });

    effect(() => {
      const ts = this.tradeStats();
      const r = this.risk();
      if (ts && r) this.updateRadar();
    });

    // Update drawdown chart for risks tab - react to period changes
    effect(() => {
      const period = this.activeDrawdownPeriod();
      const daily = this.mt5.dailyDrawdown();
      const weekly = this.mt5.weeklyDrawdown();
      const monthly = this.mt5.monthlyDrawdown();
      const yearly = this.mt5.yearlyDrawdown();
      this.updateDrawdownChartByPeriod(period, daily, weekly, monthly, yearly);
    });
  }

  dashboard = computed(() => this.mt5.dashboard());
  account = computed(() => this.dashboard()?.account);
  stats = computed(() => this.dashboard()?.stats);
  tradeStats = computed(() => this.dashboard()?.trade_stats);
  risk = computed(() => this.dashboard()?.risk_metrics);
  positions = computed(() => this.dashboard()?.open_positions || []);
  monthlyGrowth = computed(() => this.dashboard()?.monthly_growth || []);
  trades = computed(() => this.mt5.trades());
  status = computed(() => this.mt5.connectionStatus());
  error = computed(() => this.mt5.error());
  isConnected = computed(() => this.status()?.connected ?? false);

  monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  weekNumbers = Array.from({ length: 52 }, (_, i) => i + 1);
  currency = computed(() => this.account()?.currency || 'EUR');
  monthlyDrawdown = computed(() => this.mt5.monthlyDrawdown());
  dailyDrawdown = computed(() => this.mt5.dailyDrawdown());
  weeklyDrawdown = computed(() => this.mt5.weeklyDrawdown());
  yearlyDrawdown = computed(() => this.mt5.yearlyDrawdown());

  totalGrowth = computed(() => {
    const data = this.monthlyGrowth();
    if (!data.length) return null;
    let total = 0;
    for (const year of data) {
      if (year.year_total != null) total += year.year_total;
    }
    return total;
  });

  totalValue = computed(() => {
    const data = this.monthlyGrowth();
    if (!data.length) return null;
    let total = 0;
    for (const year of data) {
      if (year.year_total_value != null) total += year.year_total_value;
    }
    return total;
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
      y: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 } } }
    }
  };

  // Radar Chart
  radarData: ChartConfiguration<'radar'>['data'] = {
    labels: ['Algo trading', 'Bénéfice trades', 'Perte trades', 'Activité', 'Charge dépôt', 'Prélèvement max'],
    datasets: [{
      data: [0, 0, 0, 0, 0, 0],
      backgroundColor: 'rgba(59, 130, 246, 0.2)',
      borderColor: '#3b82f6',
      borderWidth: 2,
      pointBackgroundColor: '#3b82f6'
    }]
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

  // Drawdown History Chart (for Risks tab)
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

  ngOnInit(): void {
    this.mt5.startPolling();
  }

  setTab(tab: TabType): void {
    this.activeTab.set(tab);
  }

  setChart(mode: ChartMode): void {
    this.activeChart.set(mode);
    this.updateChart(this.mt5.history());
  }

  setTimeframe(tf: Timeframe): void {
    this.activeTimeframe.set(tf);
    this.updateChart(this.mt5.history());
  }

  setDrawdownPeriod(period: DrawdownPeriod): void {
    this.activeDrawdownPeriod.set(period);
  }

  refresh(): void {
    this.mt5.refresh();
  }

  getTimeframeMinutes(tf: Timeframe): number {
    const map: Record<Timeframe, number> = {
      '1H': 60, '1D': 1440, '1W': 10080,
      '1M': 43200, '1Y': 525600, 'All': Infinity
    };
    return map[tf];
  }

  filterHistoryByTimeframe(history: HistoryPoint[]): HistoryPoint[] {
    const tf = this.activeTimeframe();
    if (tf === 'All') return history;

    const minutes = this.getTimeframeMinutes(tf);
    const cutoff = new Date(Date.now() - minutes * 60 * 1000);

    const filtered = history.filter(h => new Date(h.timestamp) >= cutoff);

    // Si pas de données dans la période, retourner tout l'historique
    if (filtered.length === 0) return history;

    return filtered;
  }

  updateChart(history: HistoryPoint[]): void {
    if (!history.length) return;

    const filtered = this.filterHistoryByTimeframe(history);
    if (!filtered.length) return;

    const tf = this.activeTimeframe();
    const formatOptions: Intl.DateTimeFormatOptions =
      tf === '1H'
        ? { hour: '2-digit', minute: '2-digit' }
        : tf === '1D' || tf === '1W'
        ? { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }
        : { day: '2-digit', month: '2-digit', year: '2-digit' };

    const labels = filtered.map(h => new Date(h.timestamp).toLocaleString('fr-FR', formatOptions));
    const mode = this.activeChart();

    if (mode === 'growth') {
      // Affiche les deux courbes superposées: Solde (balance) et Fonds propres (equity)
      this.chartData = {
        labels,
        datasets: [
          {
            label: 'Solde',
            data: filtered.map(h => h.balance),
            borderColor: '#22c55e',
            backgroundColor: 'rgba(34,197,94,0.1)',
            fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2
          },
          {
            label: 'Fonds propres',
            data: filtered.map(h => h.equity),
            borderColor: '#3b82f6',
            backgroundColor: 'transparent',
            fill: false, tension: 0.3, pointRadius: 0, borderWidth: 2
          }
        ]
      };
    } else {
      this.chartData = {
        labels,
        datasets: [{
          label: 'Prélèvement',
          data: filtered.map(h => h.drawdown_percent),
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245,158,11,0.1)',
          fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2
        }]
      };
    }
  }

  updateRadar(): void {
    const ts = this.tradeStats();
    const r = this.risk();
    if (!ts || !r) return;

    const algoTrading = 98; // Placeholder
    const winRate = Math.min(ts.win_rate, 100);
    const lossRate = 100 - winRate;
    const activity = Math.min((ts.total_trades / 500) * 100, 100);
    const depositLoad = Math.min(r.max_deposit_load, 100);
    const maxDD = Math.min(r.max_drawdown_percent, 100);

    this.radarData = {
      labels: ['Algo trading', 'Bénéfice trades', 'Perte trades', 'Activité', 'Charge dépôt', 'Prélèvement max'],
      datasets: [{
        data: [algoTrading, winRate, lossRate, activity, depositLoad, maxDD],
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        borderColor: '#3b82f6',
        borderWidth: 2,
        pointBackgroundColor: '#3b82f6'
      }]
    };
  }

  updateDrawdownChartByPeriod(
    period: DrawdownPeriod,
    daily: DailyDrawdown[],
    weekly: WeeklyDrawdown[],
    monthly: MonthlyDrawdown[],
    yearly: YearlyDrawdown[]
  ): void {
    let labels: string[] = [];
    let data: number[] = [];

    if (period === 'day' && daily.length) {
      labels = daily.map(d => d.date);
      data = daily.map(d => d.drawdown_percent);
    } else if (period === 'week' && weekly.length) {
      labels = weekly.map(w => `S${w.week} ${w.year}`);
      data = weekly.map(w => w.drawdown_percent);
    } else if (period === 'month' && monthly.length) {
      // Flatten monthly data to show each month
      for (const year of monthly) {
        for (const month of this.monthNames) {
          if (year.months[month] != null) {
            labels.push(`${month} ${year.year}`);
            data.push(year.months[month]!);
          }
        }
      }
    } else if (period === 'year' && yearly.length) {
      labels = yearly.map(y => y.year.toString());
      data = yearly.map(y => y.drawdown_percent);
    }

    if (!labels.length) return;

    this.drawdownChartData = {
      labels,
      datasets: [{
        label: 'Drawdown %',
        data,
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.2)',
        fill: true,
        tension: 0.3,
        pointRadius: period === 'year' ? 4 : 0,
        borderWidth: 2
      }]
    };
  }

  getBarPercent(value: number | null | undefined, max: number | null | undefined): number {
    if (!value || !max || max === 0) return 0;
    return Math.min(Math.max((value / max) * 100, 0), 100);
  }

  resetDrawdown(): void {
    this.mt5.resetDrawdown().subscribe();
  }

  setMonthlyDisplay(mode: MonthlyDisplayMode): void {
    this.monthlyDisplayMode.set(mode);
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

  maxDrawdownTotal = computed(() => {
    const data = this.monthlyDrawdown();
    if (!data.length) return null;
    let max = 0;
    for (const year of data) {
      if (year.year_max != null && year.year_max > max) {
        max = year.year_max;
      }
    }
    return max > 0 ? max : null;
  });
}
