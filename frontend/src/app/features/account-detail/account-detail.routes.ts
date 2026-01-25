import { Routes } from '@angular/router';

export const ACCOUNT_DETAIL_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/account-detail-page/account-detail-page.component').then(m => m.AccountDetailPageComponent)
  }
];
