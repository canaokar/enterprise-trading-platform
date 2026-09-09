import { Component, inject, signal } from '@angular/core';
import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { forkJoin, switchMap } from 'rxjs';

import { toApiError } from '../../core/api-error';
import { MarketQuote, PortfolioSummary, PricedPosition } from '../../core/models/extension-api';
import { AccountResponse } from '../../core/models/trade-api';
import { AccountService } from '../../core/services/account-service';
import { AuthService } from '../../core/services/auth-service';
import { ExtensionService } from '../../core/services/extension-service';

/**
 * The landing screen: who you are, what cash you hold, what you are holding, and where to go
 * next.
 *
 * The three account endpoints are fetched together with `forkJoin` rather than one after
 * another. They do not depend on each other, and three sequential round trips is three times
 * the latency for no reason.
 */
@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, CurrencyPipe, DecimalPipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard {
  private readonly accounts = inject(AccountService);
  private readonly auth = inject(AuthService);
  private readonly extensions = inject(ExtensionService);

  readonly account = signal<AccountResponse | null>(null);
  readonly portfolio = signal<PortfolioSummary | null>(null);
  readonly positions = signal<PricedPosition[]>([]);
  readonly quotes = signal<MarketQuote[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.auth
      .requireAccountId()
      .pipe(
        switchMap((accountId) =>
          forkJoin({
            account: this.accounts.getAccount(accountId),
            portfolio: this.extensions.getPortfolio(accountId),
            positions: this.extensions.getPricedPositions(accountId),
            quotes: this.extensions.getMarketQuotes(),
          }),
        ),
      )
      .subscribe({
        next: (result) => {
          this.account.set(result.account);
          this.portfolio.set(result.portfolio);
          this.positions.set(result.positions);
          this.quotes.set(result.quotes);
          this.loading.set(false);
        },
        error: (failure: unknown) => {
          this.error.set(toApiError(failure).message);
          this.loading.set(false);
        },
      });
  }

}
