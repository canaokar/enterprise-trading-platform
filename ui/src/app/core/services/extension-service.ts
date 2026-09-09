import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  NotificationChannel,
  NotificationResponse,
  MarketQuote,
  PnlResponse,
  PortfolioSummary,
  PreferenceResponse,
  PriceAlert,
  PricedPosition,
  WatchlistDetail,
  WatchlistSummary,
} from '../models/extension-api';

@Injectable({ providedIn: 'root' })
export class ExtensionService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.tradeApiBaseUrl}/api/v1`;

  getPreferences(accountId: number): Observable<PreferenceResponse> {
    return this.http.get<PreferenceResponse>(`${this.baseUrl}/preferences/${accountId}`);
  }

  updateNotificationChannel(accountId: number, channel: NotificationChannel): Observable<PreferenceResponse> {
    return this.http.put<PreferenceResponse>(`${this.baseUrl}/preferences/${accountId}/notifications`, { channel });
  }

  updateDisplay(accountId: number, currency: string, theme: string): Observable<PreferenceResponse> {
    return this.http.put<PreferenceResponse>(`${this.baseUrl}/preferences/${accountId}/display`, { currency, theme });
  }

  getNotifications(accountId: number): Observable<NotificationResponse[]> {
    return this.http.get<NotificationResponse[]>(`${this.baseUrl}/notifications/${accountId}`);
  }

  markNotificationsRead(accountId: number): Observable<{ updated: number }> {
    return this.http.post<{ updated: number }>(`${this.baseUrl}/notifications/${accountId}/read`, {});
  }

  getPortfolio(accountId: number): Observable<PortfolioSummary> {
    return this.http.get<PortfolioSummary>(`${this.baseUrl}/portfolio/${accountId}`);
  }

  getPricedPositions(accountId: number): Observable<PricedPosition[]> {
    return this.http.get<PricedPosition[]>(`${this.baseUrl}/portfolio/${accountId}/positions`);
  }

  getPnl(accountId: number): Observable<PnlResponse> {
    return this.http.get<PnlResponse>(`${this.baseUrl}/portfolio/${accountId}/pnl?bySymbol=true`);
  }

  getMarketQuotes(): Observable<MarketQuote[]> {
    return this.http.get<MarketQuote[]>(`${this.baseUrl}/market/quotes`);
  }

  getWatchlists(): Observable<WatchlistSummary[]> {
    return this.http.get<WatchlistSummary[]>(`${this.baseUrl}/watchlists`);
  }

  getWatchlist(id: string): Observable<WatchlistDetail> {
    return this.http.get<WatchlistDetail>(`${this.baseUrl}/watchlists/${id}`);
  }

  createWatchlist(name: string): Observable<WatchlistDetail> {
    return this.http.post<WatchlistDetail>(`${this.baseUrl}/watchlists`, { name });
  }

  addInstrument(id: string, symbol: string): Observable<WatchlistDetail> {
    return this.http.post<WatchlistDetail>(`${this.baseUrl}/watchlists/${id}/instruments`, { symbol });
  }

  removeInstrument(id: string, symbol: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/watchlists/${id}/instruments/${symbol}`);
  }

  getAlerts(): Observable<PriceAlert[]> {
    return this.http.get<PriceAlert[]>(`${this.baseUrl}/alerts`);
  }

  createAlert(symbol: string, direction: string, threshold: number): Observable<PriceAlert> {
    return this.http.post<PriceAlert>(`${this.baseUrl}/alerts`, { symbol, direction, threshold });
  }

  disableAlert(id: string): Observable<PriceAlert> {
    return this.http.delete<PriceAlert>(`${this.baseUrl}/alerts/${id}`);
  }
}
