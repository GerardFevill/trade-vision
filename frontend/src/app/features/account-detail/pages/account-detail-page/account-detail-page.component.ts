import { Component, OnInit, computed, effect, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartType } from 'chart.js';

import { AnalyticsApiService, AccountsApiService, HistoryPoint, DailyDrawdown } from '@app/data-access';
import { SparklineComponent } from '@app/shared';

import {
  Chart, LineController, LineElement, PointElement,
  LinearScale, CategoryScale, Filler, Tooltip, Legend,
  RadarController, RadialLinearScale
} from 'chart.js';

import { Timeframe, ChartMode } from '../../charts/chart-helpers';
import { EQUITY_CHART_TYPE, EQUITY_CHART_OPTIONS, buildEquityChartData } from '../../charts/equity-chart.config';
import { RADAR_OPTIONS, RADAR_LABELS, buildRadarData } from '../../charts/radar-chart.config';
import { DRAWDOWN_CHART_OPTIONS, buildDrawdownChartData } from '../../charts/drawdown-chart.config';

Chart.register(
  LineController, LineElement, PointElement, LinearScale, CategoryScale,
  Filler, Tooltip, Legend, RadarController, RadialLinearScale
);

type TabType = 'account' | 'history' | 'statistics' | 'risks';
type MonthlyDisplayMode = 'percent' | 'value';

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
  loading = computed(() => this.analyticsApi.loading());
  lastUpdate = computed(() => this.analyticsApi.lastUpdate());
  dashboard = computed(() => this.analyticsApi.dashboard());
  account = computed(() => this.dashboard()?.account);
  stats = computed(() => this.dashboard()?.stats);
  tradeStats = computed(() => this.dashboard()?.trade_stats);
  risk = computed(() => this.dashboard()?.risk_metrics);
  positions = computed(() => this.dashboard()?.open_positions || []);
  monthlyGrowth = computed(() => this.dashboard()?.monthly_growth || []);
  trades = computed(() => this.analyticsApi.trades());
  status = computed(() => this.analyticsApi.connectionStatus());
  error = computed(() => this.analyticsApi.error());
  isConnected = computed(() => this.status()?.connected ?? false);
  currency = computed(() => this.account()?.currency || 'EUR');
  dailyDrawdown = computed(() => this.analyticsApi.dailyDrawdown());
  sparklineData = computed(() => this.analyticsApi.sparkline());

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

  // Chart state
  chartType: ChartType = EQUITY_CHART_TYPE;
  chartData: ChartConfiguration['data'] = { labels: [], datasets: [] };
  chartOptions: ChartConfiguration['options'] = EQUITY_CHART_OPTIONS;

  radarData: ChartConfiguration<'radar'>['data'] = {
    labels: RADAR_LABELS,
    datasets: [{ data: [0, 0, 0, 0, 0, 0], backgroundColor: 'rgba(59, 130, 246, 0.2)', borderColor: '#3b82f6', borderWidth: 2, pointBackgroundColor: '#3b82f6' }]
  };
  radarOptions = RADAR_OPTIONS;

  drawdownChartData: ChartConfiguration['data'] = { labels: [], datasets: [] };
  drawdownChartOptions = DRAWDOWN_CHART_OPTIONS;

  constructor(
    private analyticsApi: AnalyticsApiService,
    private accountsApi: AccountsApiService,
    private router: Router
  ) {
    effect(() => {
      const history = this.analyticsApi.history();
      const tf = this.activeTimeframe();
      const mode = this.activeChart();
      if (history.length) {
        const result = buildEquityChartData(history, tf, mode);
        this.chartData = result.data;
        this.chartOptions = result.options;
      }
    });

    effect(() => {
      const ts = this.tradeStats();
      const r = this.risk();
      if (ts && r) {
        this.radarData = buildRadarData(ts, r);
      }
    });

    effect(() => {
      const daily = this.analyticsApi.dailyDrawdown();
      if (daily.length) {
        this.drawdownChartData = buildDrawdownChartData(daily);
      }
    });
  }

  ngOnInit(): void {
    this.analyticsApi.startPolling();
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

  // Refresh from cache/DB
  refresh(): void {
    this.analyticsApi.refresh();
  }

  // Sync from MT5 (force refresh from MetaTrader)
  syncing = signal<boolean>(false);

  syncFromMT5(): void {
    const status = this.status();
    if (!status?.account) return;

    this.syncing.set(true);
    this.accountsApi.syncAccount(status.account, true).subscribe({
      next: () => {
        // After sync, refresh from DB
        this.analyticsApi.refresh();
        this.syncing.set(false);
      },
      error: () => {
        this.syncing.set(false);
      }
    });
  }

  resetDrawdown(): void {
    this.analyticsApi.resetDrawdown().subscribe();
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
}
