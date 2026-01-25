import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, of } from 'rxjs';

import {
  AccountSummary,
  ConnectionStatus,
  FullDashboard,
  HistoryPoint,
  Trade,
  DailyDrawdown,
  SparklineData,
  GlobalMonthlyGrowth
} from '../models';

/**
 * MT5 API Service
 * Handles all HTTP communication with the backend
 */
@Injectable({ providedIn: 'root' })
export class Mt5ApiService {
  private readonly apiUrl = 'http://localhost:8000/api';

  // Reactive state signals
  readonly dashboard = signal<FullDashboard | null>(null);
  readonly history = signal<HistoryPoint[]>([]);
  readonly trades = signal<Trade[]>([]);
  readonly dailyDrawdown = signal<DailyDrawdown[]>([]);
  readonly connectionStatus = signal<ConnectionStatus | null>(null);
  readonly sparkline = signal<number[]>([]);
  readonly error = signal<string | null>(null);
  readonly loading = signal<boolean>(false);
  readonly lastUpdate = signal<Date | null>(null);

  constructor(private http: HttpClient) {}

  // Account endpoints
  getAccounts(): Observable<AccountSummary[]> {
    return this.http.get<AccountSummary[]>(`${this.apiUrl}/accounts`);
  }

  connectToAccount(accountId: number): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/accounts/${accountId}/connect`, {});
  }

  getStatus(): Observable<ConnectionStatus> {
    return this.http.get<ConnectionStatus>(`${this.apiUrl}/status`);
  }

  // Dashboard endpoint
  getDashboard(): Observable<FullDashboard> {
    return this.http.get<FullDashboard>(`${this.apiUrl}/dashboard`);
  }

  // History endpoints
  getHistory(limit = 60): Observable<HistoryPoint[]> {
    return this.http.get<HistoryPoint[]>(`${this.apiUrl}/history?limit=${limit}`);
  }

  // Trade endpoints
  getTrades(days = 30): Observable<Trade[]> {
    return this.http.get<Trade[]>(`${this.apiUrl}/trades?days=${days}`);
  }

  // Analytics endpoints
  getDailyDrawdown(): Observable<DailyDrawdown[]> {
    return this.http.get<DailyDrawdown[]>(`${this.apiUrl}/daily-drawdown`);
  }

  resetDrawdown(): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/reset-drawdown`, {});
  }

  getSparklines(points = 20): Observable<SparklineData> {
    return this.http.get<SparklineData>(`${this.apiUrl}/sparklines?points=${points}`);
  }

  getGlobalMonthlyGrowth(): Observable<GlobalMonthlyGrowth[]> {
    return this.http.get<GlobalMonthlyGrowth[]>(`${this.apiUrl}/global-monthly-growth`);
  }

  // Data refresh
  refresh(): void {
    this.loading.set(true);
    this.error.set(null);

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
    this.getStatus().pipe(catchError(() => of(null))).subscribe(data => {
      if (data) {
        this.connectionStatus.set(data);
        if (data.account) {
          this.getSparklines(100).pipe(catchError(() => of({} as SparklineData))).subscribe(sparklines => {
            const accountSparkline = sparklines[data.account!];
            if (accountSparkline) this.sparkline.set(accountSparkline);
          });
        }
      }
    });
    this.getTrades(365).pipe(catchError(() => of([]))).subscribe(data => this.trades.set(data));
    this.getDailyDrawdown().pipe(catchError(() => of([]))).subscribe(data => this.dailyDrawdown.set(data));
  }

  startPolling(): void {
    this.refresh();
  }
}
