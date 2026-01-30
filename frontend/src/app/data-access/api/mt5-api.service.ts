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

import {
  Portfolio,
  PortfolioSummary,
  PortfolioDetail,
  CreatePortfolioRequest,
  UpdatePortfolioRequest,
  AddAccountRequest,
  MonthlySnapshot,
  CurrentMonthPreview,
  UpdateWithdrawalRequest
} from '../models/portfolio.model';

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

  // Portfolio endpoints
  getPortfolioTypes(): Observable<{ types: Record<string, number[]>; all_factors: number[] }> {
    return this.http.get<{ types: Record<string, number[]>; all_factors: number[] }>(
      `${this.apiUrl}/portefeuilles/types`
    );
  }

  getPortfolioClients(): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/portefeuilles/clients`);
  }

  getUsedAccountIds(): Observable<number[]> {
    return this.http.get<number[]>(`${this.apiUrl}/portefeuilles/used-accounts`);
  }

  getPortfolios(client?: string): Observable<PortfolioSummary[]> {
    const url = client
      ? `${this.apiUrl}/portefeuilles?client=${encodeURIComponent(client)}`
      : `${this.apiUrl}/portefeuilles`;
    return this.http.get<PortfolioSummary[]>(url);
  }

  getPortfolio(id: number): Observable<PortfolioDetail> {
    return this.http.get<PortfolioDetail>(`${this.apiUrl}/portefeuilles/${id}`);
  }

  createPortfolio(request: CreatePortfolioRequest): Observable<Portfolio> {
    return this.http.post<Portfolio>(`${this.apiUrl}/portefeuilles`, request);
  }

  updatePortfolio(id: number, request: UpdatePortfolioRequest): Observable<Portfolio> {
    return this.http.put<Portfolio>(`${this.apiUrl}/portefeuilles/${id}`, request);
  }

  deletePortfolio(id: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/portefeuilles/${id}`);
  }

  addAccountToPortfolio(portfolioId: number, request: AddAccountRequest): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/accounts`,
      request
    );
  }

  removeAccountFromPortfolio(portfolioId: number, accountId: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/accounts/${accountId}`
    );
  }

  // Monthly records endpoints
  getMonthlyHistory(portfolioId: number): Observable<{ months: string[] }> {
    return this.http.get<{ months: string[] }>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/monthly`
    );
  }

  getMonthlySnapshot(portfolioId: number, month: string): Observable<MonthlySnapshot> {
    return this.http.get<MonthlySnapshot>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/monthly/${month}`
    );
  }

  createMonthlySnapshot(portfolioId: number, month: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/monthly/${month}`,
      {}
    );
  }

  closeMonthlySnapshot(portfolioId: number, month: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/monthly/${month}/close`,
      {}
    );
  }

  updateMonthlyWithdrawals(
    portfolioId: number,
    month: string,
    withdrawals: UpdateWithdrawalRequest[]
  ): Observable<{ message: string }> {
    return this.http.put<{ message: string }>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/monthly/${month}`,
      { withdrawals }
    );
  }

  getCurrentMonthPreview(portfolioId: number): Observable<CurrentMonthPreview> {
    return this.http.get<CurrentMonthPreview>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/monthly-current`
    );
  }

  updateStartingBalance(portfolioId: number, accountId: number, startingBalance: number): Observable<any> {
    return this.http.put(
      `${this.apiUrl}/portefeuilles/${portfolioId}/monthly-current/starting-balance`,
      { account_id: accountId, starting_balance: startingBalance }
    );
  }

  closeCurrentMonth(portfolioId: number): Observable<{ message: string; phase?: number; accounts_closed: number }> {
    return this.http.post<{ message: string; phase?: number; accounts_closed: number }>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/monthly-current/close`,
      {}
    );
  }

  getEliteMonthlyHistory(portfolioId: number, month: string): Observable<any> {
    return this.http.get<any>(
      `${this.apiUrl}/portefeuilles/${portfolioId}/monthly/${month}/elite`
    );
  }
}
