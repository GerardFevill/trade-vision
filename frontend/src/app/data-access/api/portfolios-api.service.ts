import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  Portfolio,
  PortfolioSummary,
  PortfolioDetail,
  CreatePortfolioRequest,
  UpdatePortfolioRequest,
  AddAccountRequest,
} from '../models/portfolio.model';

@Injectable({ providedIn: 'root' })
export class PortfoliosApiService {
  private readonly apiUrl = '/api';

  constructor(private http: HttpClient) {}

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
}
