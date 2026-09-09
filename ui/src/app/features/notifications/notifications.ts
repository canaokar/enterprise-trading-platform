import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { switchMap } from 'rxjs';

import { toApiError } from '../../core/api-error';
import { NotificationResponse } from '../../core/models/extension-api';
import { AuthService } from '../../core/services/auth-service';
import { ExtensionService } from '../../core/services/extension-service';

@Component({
  selector: 'app-notifications',
  imports: [DatePipe],
  templateUrl: './notifications.html',
  styleUrl: './notifications.css',
})
export class Notifications {
  private readonly auth = inject(AuthService);
  private readonly extensions = inject(ExtensionService);

  readonly items = signal<NotificationResponse[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.auth.requireAccountId().pipe(
      switchMap((accountId) => this.extensions.getNotifications(accountId)),
    ).subscribe({
      next: (items) => { this.items.set(items); this.loading.set(false); },
      error: (failure: unknown) => { this.error.set(toApiError(failure).message); this.loading.set(false); },
    });
  }

  markAllRead(): void {
    this.auth.requireAccountId().pipe(
      switchMap((accountId) => this.extensions.markNotificationsRead(accountId)),
    ).subscribe({
      next: () => this.load(),
      error: (failure: unknown) => this.error.set(toApiError(failure).message),
    });
  }
}
