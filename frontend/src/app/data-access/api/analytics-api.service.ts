import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, of } from 'rxjs';

import {
  FullDashboard,
  HistoryPoint,
  Trade,
  DailyDrawdown,
  ConnectionStatus,
  SparklineData,
  GlobalMonthlyGrowth
} from '../models';

import { AccountsApiService } from './accounts-api.service';

@Injectable({ providedIn: 'root' })
export class AnalyticsApiService {
  private readonly apiUrl = '/api';

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

  constructor(
    private http: HttpClient,
    private accountsApi: AccountsApiService
  ) {}

  getDashboard(): Observable<FullDashboard> {
    return this.http.get<FullDashboard>(`${this.apiUrl}/dashboard`);
  }

  getHistory(limit = 60): Observable<HistoryPoint[]> {
    return this.http.get<HistoryPoint[]>(`${this.apiUrl}/history?limit=${limit}`);
  }

  getTrades(days = 30): Observable<Trade[]> {
    return this.http.get<Trade[]>(`${this.apiUrl}/trades?days=${days}`);
  }

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
    this.accountsApi.getStatus().pipe(catchError(() => of(null))).subscribe(data => {
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
