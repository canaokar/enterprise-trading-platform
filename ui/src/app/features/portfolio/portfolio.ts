import { CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { forkJoin, switchMap } from 'rxjs';

import { toApiError } from '../../core/api-error';
import { PnlResponse, PortfolioSummary, PricedPosition } from '../../core/models/extension-api';
import { AuthService } from '../../core/services/auth-service';
import { ExtensionService } from '../../core/services/extension-service';

@Component({
  selector: 'app-portfolio',
  imports: [CurrencyPipe, DatePipe, DecimalPipe],
  templateUrl: './portfolio.html',
  styleUrl: './portfolio.css',
})
export class Portfolio {
  private readonly auth = inject(AuthService);
  private readonly extensions = inject(ExtensionService);

  readonly summary = signal<PortfolioSummary | null>(null);
  readonly positions = signal<PricedPosition[]>([]);
  readonly pnl = signal<PnlResponse | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.auth.requireAccountId().pipe(
      switchMap((accountId) => forkJoin({
        summary: this.extensions.getPortfolio(accountId),
        positions: this.extensions.getPricedPositions(accountId),
        pnl: this.extensions.getPnl(accountId),
      })),
    ).subscribe({
      next: (result) => {
        this.summary.set(result.summary);
        this.positions.set(result.positions);
        this.pnl.set(result.pnl);
        this.loading.set(false);
      },
      error: (failure: unknown) => {
        this.error.set(toApiError(failure).message);
        this.loading.set(false);
      },
    });
  }
}
