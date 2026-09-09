export type NotificationChannel = 'IN_APP' | 'EMAIL' | 'SMS' | 'PUSH';

export interface PreferenceResponse {
  accountId: number;
  notificationChannel: NotificationChannel;
  displayCurrency: string;
  theme: 'LIGHT' | 'DARK' | 'SYSTEM';
  updatedOn: string;
}

export interface NotificationResponse {
  id: string;
  accountId: number;
  type: string;
  channel: NotificationChannel;
  subject: string;
  message: string;
  deliveryState: string;
  readOn?: string | null;
  createdOn: string;
}

export interface PortfolioSummary {
  accountId: number;
  baseCurrency: string;
  cashBalance: number;
  marketValue: number;
  costBasis: number;
  unrealisedPnl: number;
  unrealisedPnlPercent: number;
  realisedPnl: number;
  totalValue: number;
  positionCount: number;
  partial: boolean;
  asOf: string;
}

export interface PricedPosition {
  accountId: number;
  symbol: string;
  quantity: number;
  averageCost: number;
  costBasis: number;
  lastPrice?: number | null;
  marketValue?: number | null;
  unrealisedPnl?: number | null;
  unrealisedPnlPercent?: number | null;
  currency: string;
  priceAsOf?: string | null;
  stale: boolean;
}

export interface SymbolPnl {
  symbol: string;
  realisedPnl: number;
  unrealisedPnl: number;
  totalPnl: number;
}

export interface PnlResponse {
  accountId: number;
  baseCurrency: string;
  from?: string | null;
  to?: string | null;
  realisedPnl: number;
  unrealisedPnl: number;
  totalPnl: number;
  bySymbol: SymbolPnl[];
  asOf: string;
}

export interface WatchlistSummary {
  id: string;
  name: string;
  instrumentCount: number;
  createdOn: string;
}

export interface WatchlistEntry {
  symbol: string;
  price?: number | null;
  currency?: string | null;
  quoteAsOf?: string | null;
  stale: boolean;
}

export interface WatchlistDetail {
  id: string;
  accountId: number;
  name: string;
  instruments: WatchlistEntry[];
  createdOn: string;
}

export interface PriceAlert {
  id: string;
  accountId: number;
  symbol: string;
  direction: 'ABOVE' | 'BELOW';
  threshold: number;
  status: 'ACTIVE' | 'TRIGGERED' | 'DISABLED';
  createdOn: string;
  triggeredOn?: string | null;
  triggeredPrice?: number | null;
}

export interface MarketQuote {
  symbol: string;
  price: number;
  currency: string;
  quoteAsOf: string;
  stale: boolean;
  marketState: string;
  feedMode: 'live' | 'fixture';
  receivedOn: string;
}
