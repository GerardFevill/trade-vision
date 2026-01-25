import { Routes } from '@angular/router';

export const ACCOUNTS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/accounts-page/accounts-page.component').then(m => m.AccountsPageComponent)
  }
];
