import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/accounts',
    pathMatch: 'full'
  },
  {
    path: 'accounts',
    loadChildren: () =>
      import('./features/accounts/accounts.routes').then(m => m.ACCOUNTS_ROUTES),
    title: 'Comptes MT5'
  },
  {
    path: 'accounts/:id',
    loadChildren: () =>
      import('./features/account-detail/account-detail.routes').then(m => m.ACCOUNT_DETAIL_ROUTES),
    title: 'Détails du compte'
  },
  {
    path: 'portfolios',
    loadChildren: () =>
      import('./features/portfolios/portfolios.routes').then(m => m.PORTFOLIOS_ROUTES),
    title: 'Portefeuilles'
  }
];
