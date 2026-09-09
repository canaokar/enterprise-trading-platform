import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth-guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  {
    path: 'login',
    title: 'Sign in',
    loadComponent: () => import('./features/login/login').then((m) => m.Login),
  },
  {
    path: 'dashboard',
    title: 'Dashboard',
    canActivate: [authGuard],
    loadComponent: () => import('./features/dashboard/dashboard').then((m) => m.Dashboard),
  },
  {
    path: 'orders/new',
    title: 'Order ticket',
    canActivate: [authGuard],
    loadComponent: () => import('./features/order-ticket/order-ticket').then((m) => m.OrderTicket),
  },
  {
    path: 'orders',
    title: 'Order history',
    canActivate: [authGuard],
    loadComponent: () => import('./features/blotter/blotter').then((m) => m.Blotter),
  },
  {
    path: 'portfolio',
    title: 'Portfolio and P&L',
    canActivate: [authGuard],
    loadComponent: () => import('./features/portfolio/portfolio').then((m) => m.Portfolio),
  },
  {
    path: 'preferences',
    title: 'Preferences',
    canActivate: [authGuard],
    loadComponent: () => import('./features/preferences/preferences').then((m) => m.Preferences),
  },
  {
    path: 'notifications',
    title: 'Notifications',
    canActivate: [authGuard],
    loadComponent: () => import('./features/notifications/notifications').then((m) => m.Notifications),
  },
  {
    path: 'watchlists',
    title: 'Watchlists and alerts',
    canActivate: [authGuard],
    loadComponent: () => import('./features/watchlists/watchlists').then((m) => m.Watchlists),
  },
  { path: '**', redirectTo: 'dashboard' },
];
