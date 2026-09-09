import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin, switchMap } from 'rxjs';

import { toApiError } from '../../core/api-error';
import { NotificationChannel, PreferenceResponse } from '../../core/models/extension-api';
import { AuthService } from '../../core/services/auth-service';
import { ExtensionService } from '../../core/services/extension-service';

@Component({
  selector: 'app-preferences',
  imports: [ReactiveFormsModule, DatePipe],
  templateUrl: './preferences.html',
  styleUrl: './preferences.css',
})
export class Preferences {
  private readonly auth = inject(AuthService);
  private readonly extensions = inject(ExtensionService);
  private readonly fb = inject(FormBuilder);

  readonly form = this.fb.nonNullable.group({
    channel: ['IN_APP' as NotificationChannel, Validators.required],
    currency: ['USD', [Validators.required, Validators.pattern(/^[A-Z]{3}$/)]],
    theme: ['SYSTEM', Validators.required],
  });
  readonly preference = signal<PreferenceResponse | null>(null);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly saved = signal(false);

  constructor() {
    this.auth.requireAccountId().pipe(
      switchMap((accountId) => this.extensions.getPreferences(accountId)),
    ).subscribe({
      next: (preference) => {
        this.preference.set(preference);
        this.form.setValue({
          channel: preference.notificationChannel,
          currency: preference.displayCurrency,
          theme: preference.theme,
        });
        this.loading.set(false);
      },
      error: (failure: unknown) => {
        this.error.set(toApiError(failure).message);
        this.loading.set(false);
      },
    });
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.saved.set(false);
    this.error.set(null);
    const value = this.form.getRawValue();
    this.auth.requireAccountId().pipe(
      switchMap((accountId) => forkJoin([
        this.extensions.updateNotificationChannel(accountId, value.channel),
        this.extensions.updateDisplay(accountId, value.currency.toUpperCase(), value.theme),
      ])),
    ).subscribe({
      next: ([, preference]) => {
        this.preference.set(preference);
        this.saving.set(false);
        this.saved.set(true);
      },
      error: (failure: unknown) => {
        this.error.set(toApiError(failure).message);
        this.saving.set(false);
      },
    });
  }
}
