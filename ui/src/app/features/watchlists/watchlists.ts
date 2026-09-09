import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin } from 'rxjs';

import { toApiError } from '../../core/api-error';
import { PriceAlert, WatchlistDetail, WatchlistSummary } from '../../core/models/extension-api';
import { ExtensionService } from '../../core/services/extension-service';

@Component({
  selector: 'app-watchlists',
  imports: [ReactiveFormsModule, CurrencyPipe, DatePipe],
  templateUrl: './watchlists.html',
  styleUrl: './watchlists.css',
})
export class Watchlists {
  private readonly extensions = inject(ExtensionService);
  private readonly fb = inject(FormBuilder);

  readonly watchlists = signal<WatchlistSummary[]>([]);
  readonly selected = signal<WatchlistDetail | null>(null);
  readonly alerts = signal<PriceAlert[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly newListForm = this.fb.nonNullable.group({ name: ['', [Validators.required, Validators.maxLength(80)]] });
  readonly instrumentForm = this.fb.nonNullable.group({ symbol: ['', [Validators.required, Validators.maxLength(20)]] });
  readonly alertForm = this.fb.nonNullable.group({
    symbol: ['AAPL', [Validators.required, Validators.maxLength(20)]],
    direction: ['ABOVE', Validators.required],
    threshold: [240, [Validators.required, Validators.min(0.01)]],
  });

  constructor() {
    this.load();
  }

  load(preferredId?: string): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({ watchlists: this.extensions.getWatchlists(), alerts: this.extensions.getAlerts() }).subscribe({
      next: ({ watchlists, alerts }) => {
        this.watchlists.set(watchlists);
        this.alerts.set(alerts);
        const id = preferredId ?? this.selected()?.id ?? watchlists[0]?.id;
        if (id) {
          this.select(id);
        } else {
          this.selected.set(null);
          this.loading.set(false);
        }
      },
      error: (failure: unknown) => { this.error.set(toApiError(failure).message); this.loading.set(false); },
    });
  }

  select(id: string): void {
    this.loading.set(true);
    this.extensions.getWatchlist(id).subscribe({
      next: (detail) => { this.selected.set(detail); this.loading.set(false); },
      error: (failure: unknown) => { this.error.set(toApiError(failure).message); this.loading.set(false); },
    });
  }

  createWatchlist(): void {
    if (this.newListForm.invalid) return;
    this.extensions.createWatchlist(this.newListForm.getRawValue().name.trim()).subscribe({
      next: (created) => { this.newListForm.reset(); this.load(created.id); },
      error: (failure: unknown) => this.error.set(toApiError(failure).message),
    });
  }

  addInstrument(): void {
    const list = this.selected();
    if (!list || this.instrumentForm.invalid) return;
    const symbol = this.instrumentForm.getRawValue().symbol.trim().toUpperCase();
    this.extensions.addInstrument(list.id, symbol).subscribe({
      next: (detail) => { this.selected.set(detail); this.instrumentForm.reset(); this.load(detail.id); },
      error: (failure: unknown) => this.error.set(toApiError(failure).message),
    });
  }

  removeInstrument(symbol: string): void {
    const list = this.selected();
    if (!list) return;
    this.extensions.removeInstrument(list.id, symbol).subscribe({
      next: () => this.load(list.id),
      error: (failure: unknown) => this.error.set(toApiError(failure).message),
    });
  }

  createAlert(): void {
    if (this.alertForm.invalid) return;
    const value = this.alertForm.getRawValue();
    this.extensions.createAlert(value.symbol.trim().toUpperCase(), value.direction, value.threshold).subscribe({
      next: () => this.load(),
      error: (failure: unknown) => this.error.set(toApiError(failure).message),
    });
  }

  disableAlert(id: string): void {
    this.extensions.disableAlert(id).subscribe({
      next: () => this.load(),
      error: (failure: unknown) => this.error.set(toApiError(failure).message),
    });
  }
}
