import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  Firm,
  FirmWithProfiles,
  CreateFirmRequest,
  Profile,
  CreateProfileRequest
} from '../models/firm.model';

@Injectable({ providedIn: 'root' })
export class FirmsApiService {
  private readonly apiUrl = '/api';

  constructor(private http: HttpClient) {}

  getFirms(): Observable<Firm[]> {
    return this.http.get<Firm[]>(`${this.apiUrl}/firms`);
  }

  getFirm(id: number): Observable<FirmWithProfiles> {
    return this.http.get<FirmWithProfiles>(`${this.apiUrl}/firms/${id}`);
  }

  createFirm(request: CreateFirmRequest): Observable<Firm> {
    return this.http.post<Firm>(`${this.apiUrl}/firms`, request);
  }

  deleteFirm(id: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/firms/${id}`);
  }

  getProfiles(firmId?: number): Observable<Profile[]> {
    const url = firmId
      ? `${this.apiUrl}/profiles?firm_id=${firmId}`
      : `${this.apiUrl}/profiles`;
    return this.http.get<Profile[]>(url);
  }

  getProfileNames(): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/profiles/names`);
  }

  createProfile(request: CreateProfileRequest): Observable<Profile> {
    return this.http.post<Profile>(`${this.apiUrl}/profiles`, request);
  }

  deleteProfile(id: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/profiles/${id}`);
  }
}
