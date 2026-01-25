import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval, switchMap, startWith, catchError, of } from 'rxjs';

export interface AccountInfo {
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  margin_level: number | null;
  profit: number;
  leverage: number;
  server: string;
  name: string;
  login: number;
  currency: string;
  trade_mode: string;
}

export interface AccountStats {
  balance: number;
  equity: number;
  profit: number;
  drawdown: number;
  drawdown_percent: number;
  initial_deposit: number;
  total_deposits: number;
  total_withdrawals: number;
  growth_percent: number;
  timestamp: string;
}

export interface TradeStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  best_trade: number;
  worst_trade: number;
  gross_profit: number;
  gross_loss: number;
  profit_factor: number;
  average_profit: number;
  average_loss: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  longs_count: number;
  shorts_count: number;
  longs_won: number;
  shorts_won: number;
  avg_holding_time_seconds: number;
  expected_payoff: number;
}

export interface RiskMetrics {
  max_drawdown: number;
  max_drawdown_percent: number;
  relative_drawdown_balance: number;
  relative_drawdown_equity: number;
  max_deposit_load: number;
  sharpe_ratio: number;
  recovery_factor: number;
  current_drawdown: number;
  current_drawdown_percent: number;
}

export interface Trade {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  open_time: string;
  open_price: number;
  close_time: string | null;
  close_price: number | null;
  profit: number;
  commission: number;
  swap: number;
  comment: string;
}

export interface Position {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  open_time: string;
  open_price: number;
  current_price: number;
  profit: number;
  sl: number | null;
  tp: number | null;
}

export interface HistoryPoint {
  balance: number;
  equity: number;
  drawdown: number;
  drawdown_percent: number;
  timestamp: string;
}

export interface ConnectionStatus {
  connected: boolean;
  server: string | null;
  account: number | null;
  name: string | null;
  company: string | null;
}

export interface MonthlyGrowth {
  year: number;
  months: Record<string, number | null>;
  values: Record<string, number | null>;
  year_total: number | null;
  year_total_value: number | null;
}

export interface MonthlyDrawdown {
  year: number;
  months: Record<string, number | null>;
  year_max: number | null;
}

export interface DailyDrawdown {
  date: string;
  drawdown_percent: number;
  start_balance: number;
  min_balance: number;
}

export interface WeeklyDrawdown {
  year: number;
  week: number;
  start_date: string;
  drawdown_percent: number;
}

export interface YearlyDrawdown {
  year: number;
  drawdown_percent: number;
  start_balance: number;
  min_balance: number;
}

export interface FullDashboard {
  account: AccountInfo;
  stats: AccountStats;
  trade_stats: TradeStats;
  risk_metrics: RiskMetrics;
  open_positions: Position[];
  monthly_growth: MonthlyGrowth[];
}

export interface AccountSummary {
  id: number;
  name: string;
  broker: string;
  server: string;
  balance: number;
  equity: number;
  profit: number;
  profit_percent: number;
  drawdown: number;
  trades: number;
  win_rate: number;
  currency: string;
  leverage: number;
  connected: boolean;
}

export type SparklineData = Record<number, number[]>;

export interface GlobalMonthlyGrowthMonth {
  profit_eur: number;
  profit_usd: number;
}

export interface GlobalMonthlyGrowth {
  year: number;
  months: Record<string, GlobalMonthlyGrowthMonth | null>;
  year_total_eur: number;
  year_total_usd: number;
}

@Injectable({ providedIn: 'root' })
export class Mt5Service {
  private apiUrl = 'http://localhost:8000/api';

  dashboard = signal<FullDashboard | null>(null);
  history = signal<HistoryPoint[]>([]);
  trades = signal<Trade[]>([]);
  monthlyDrawdown = signal<MonthlyDrawdown[]>([]);
  dailyDrawdown = signal<DailyDrawdown[]>([]);
  weeklyDrawdown = signal<WeeklyDrawdown[]>([]);
  yearlyDrawdown = signal<YearlyDrawdown[]>([]);
  connectionStatus = signal<ConnectionStatus | null>(null);
  error = signal<string | null>(null);
  loading = signal<boolean>(false);
  lastUpdate = signal<Date | null>(null);

  constructor(private http: HttpClient) {}

  getDashboard(): Observable<FullDashboard> {
    return this.http.get<FullDashboard>(`${this.apiUrl}/dashboard`);
  }

  getAccounts(): Observable<AccountSummary[]> {
    return this.http.get<AccountSummary[]>(`${this.apiUrl}/accounts`);
  }

  connectToAccount(accountId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/accounts/${accountId}/connect`, {});
  }

  getHistory(limit = 60): Observable<HistoryPoint[]> {
    return this.http.get<HistoryPoint[]>(`${this.apiUrl}/history?limit=${limit}`);
  }

  getTrades(days = 30): Observable<Trade[]> {
    return this.http.get<Trade[]>(`${this.apiUrl}/trades?days=${days}`);
  }

  getStatus(): Observable<ConnectionStatus> {
    return this.http.get<ConnectionStatus>(`${this.apiUrl}/status`);
  }

  resetDrawdown(): Observable<any> {
    return this.http.post(`${this.apiUrl}/reset-drawdown`, {});
  }

  getMonthlyDrawdown(): Observable<MonthlyDrawdown[]> {
    return this.http.get<MonthlyDrawdown[]>(`${this.apiUrl}/monthly-drawdown`);
  }

  getDailyDrawdown(): Observable<DailyDrawdown[]> {
    return this.http.get<DailyDrawdown[]>(`${this.apiUrl}/daily-drawdown`);
  }

  getWeeklyDrawdown(): Observable<WeeklyDrawdown[]> {
    return this.http.get<WeeklyDrawdown[]>(`${this.apiUrl}/weekly-drawdown`);
  }

  getYearlyDrawdown(): Observable<YearlyDrawdown[]> {
    return this.http.get<YearlyDrawdown[]>(`${this.apiUrl}/yearly-drawdown`);
  }

  getSparklines(points = 20): Observable<SparklineData> {
    return this.http.get<SparklineData>(`${this.apiUrl}/sparklines?points=${points}`);
  }

  getGlobalMonthlyGrowth(): Observable<GlobalMonthlyGrowth[]> {
    return this.http.get<GlobalMonthlyGrowth[]>(`${this.apiUrl}/global-monthly-growth`);
  }

  refresh(): void {
    this.loading.set(true);
    this.error.set(null);

    // Fetch all data
    this.getDashboard().pipe(
      catchError(() => {
        this.error.set('Connexion perdue');
        return of(null);
      })
    ).subscribe(data => {
      if (data) {
        this.dashboard.set(data);
        this.lastUpdate.set(new Date());
      }
      this.loading.set(false);
    });

    this.getHistory(3600).pipe(catchError(() => of([]))).subscribe(data => this.history.set(data));
    this.getStatus().pipe(catchError(() => of(null))).subscribe(data => { if (data) this.connectionStatus.set(data); });
    this.getTrades(365).pipe(catchError(() => of([]))).subscribe(data => this.trades.set(data));
    this.getMonthlyDrawdown().pipe(catchError(() => of([]))).subscribe(data => this.monthlyDrawdown.set(data));
    this.getDailyDrawdown().pipe(catchError(() => of([]))).subscribe(data => this.dailyDrawdown.set(data));
    this.getWeeklyDrawdown().pipe(catchError(() => of([]))).subscribe(data => this.weeklyDrawdown.set(data));
    this.getYearlyDrawdown().pipe(catchError(() => of([]))).subscribe(data => this.yearlyDrawdown.set(data));
  }

  // Keep for backwards compatibility, just calls refresh once
  startPolling(): void {
    this.refresh();
  }
}
