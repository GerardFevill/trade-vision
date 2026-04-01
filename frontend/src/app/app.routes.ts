import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/dashboard',
    pathMatch: 'full'
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/firms-dashboard/firms-dashboard.component').then(m => m.FirmsDashboardComponent),
    title: 'Dashboard'
  },
  {
    path: 'firms',
    loadChildren: () =>
      import('./features/firms/firms.routes').then(m => m.FIRMS_ROUTES),
    title: 'Firms'
  },
  {
    path: ':firmSlug',
    children: [
      {
        path: '',
        redirectTo: 'accounts',
        pathMatch: 'full'
      },
      {
        path: 'accounts',
        loadChildren: () =>
          import('./features/accounts/accounts.routes').then(m => m.ACCOUNTS_ROUTES),
        title: 'Mes Comptes'
      },
      {
        path: 'accounts/:id',
        loadChildren: () =>
          import('./features/account-detail/account-detail.routes').then(m => m.ACCOUNT_DETAIL_ROUTES),
        title: 'Détails du compte'
      },
      {
        path: 'portifs',
        loadChildren: () =>
          import('./features/portfolios/portfolios.routes').then(m => m.PORTFOLIOS_ROUTES),
        title: 'Portefeuilles'
      }
    ]
  }
];
