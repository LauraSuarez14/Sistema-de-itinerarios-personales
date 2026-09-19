import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { PlotlyPoint } from '../models/airport.model';
import { CreateItineraryPayload, Itinerary, PageOut } from '../models/itinerary.model';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  /** Detecta el host actual en vez de asumir "localhost": así el mismo build
   * funciona igual si se accede desde otra IP de la LAN (docker-compose
   * expone el gateway en el puerto 8000 del mismo host que sirve el
   * frontend). */
  readonly apiBase = `${window.location.protocol}//${window.location.hostname}:8000`;

  constructor(private readonly http: HttpClient) {}

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiBase}/auth/login`, { username, password });
  }

  getAirportsPlotly(limit = 300): Observable<PlotlyPoint[]> {
    return this.http.get<PlotlyPoint[]>(`${this.apiBase}/api/v1/airports/plotly/points`, {
      params: { limit },
    });
  }

  listItineraries(page: number, pageSize: number): Observable<PageOut<Itinerary>> {
    return this.http.get<PageOut<Itinerary>>(`${this.apiBase}/api/v1/itineraries`, {
      params: { page, page_size: pageSize },
    });
  }

  createItinerary(payload: CreateItineraryPayload): Observable<Itinerary> {
    return this.http.post<Itinerary>(`${this.apiBase}/api/v1/itineraries`, payload);
  }

  deleteItinerary(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiBase}/api/v1/itineraries/${id}`);
  }
}
