import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  MonthlySnapshot,
  CurrentMonthPreview,
  UpdateWithdrawalRequest
} from '../models/portfolio.model';

@Injectable({ providedIn: 'root' })
export class MonthlyRecordsApiService {
  private readonly apiUrl = '/api';

  constructor(private http: HttpClient) {}

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
