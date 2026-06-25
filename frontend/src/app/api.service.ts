import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  BlockerCreate,
  EventCreate,
  EventRead,
  ParticipantJoin,
  SuggestionResponse
} from './models';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = '/api';

  constructor(private readonly http: HttpClient) {}

  createEvent(payload: EventCreate): Observable<EventRead> {
    return this.http.post<EventRead>(`${this.baseUrl}/events`, payload);
  }

  getEvent(code: string): Observable<EventRead> {
    return this.http.get<EventRead>(`${this.baseUrl}/events/${encodeURIComponent(code)}`);
  }

  joinEvent(code: string, payload: ParticipantJoin): Observable<EventRead> {
    return this.http.post<EventRead>(`${this.baseUrl}/events/${encodeURIComponent(code)}/participants`, payload);
  }

  addBlockers(code: string, payload: BlockerCreate): Observable<EventRead> {
    return this.http.post<EventRead>(`${this.baseUrl}/events/${encodeURIComponent(code)}/blockers`, payload);
  }

  deleteBlocker(code: string, blockerId: number, login: string): Observable<EventRead> {
    const params = new HttpParams().set('login', login);
    return this.http.delete<EventRead>(
      `${this.baseUrl}/events/${encodeURIComponent(code)}/blockers/${blockerId}`,
      { params }
    );
  }

  calculateSuggestions(code: string): Observable<SuggestionResponse> {
    return this.http.get<SuggestionResponse>(`${this.baseUrl}/events/${encodeURIComponent(code)}/suggestions`);
  }
}

