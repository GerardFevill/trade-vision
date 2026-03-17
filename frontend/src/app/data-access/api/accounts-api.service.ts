import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { AccountSummary, ConnectionStatus, SparklineData } from '../models';

@Injectable({ providedIn: 'root' })
export class AccountsApiService {
  private readonly apiUrl = '/api';

  constructor(private http: HttpClient) {}

  getAccounts(forceMT5 = false): Observable<AccountSummary[]> {
    const url = forceMT5
      ? `${this.apiUrl}/accounts?force_mt5=true`
      : `${this.apiUrl}/accounts`;
    return this.http.get<AccountSummary[]>(url);
  }

  connectToAccount(accountId: number): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/accounts/${accountId}/connect`, {});
  }

  getStatus(): Observable<ConnectionStatus> {
    return this.http.get<ConnectionStatus>(`${this.apiUrl}/status`);
  }

  syncFromMT5(force = true): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/sync/all?force=${force}`, {});
  }

  syncAccount(accountId: number, force = true): Observable<{ message: string; synced: boolean }> {
    return this.http.post<{ message: string; synced: boolean }>(
      `${this.apiUrl}/accounts/${accountId}/sync?force=${force}`, {}
    );
  }
}
