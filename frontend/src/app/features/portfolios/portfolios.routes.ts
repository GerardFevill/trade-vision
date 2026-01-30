import { Routes } from '@angular/router';

export const PORTFOLIOS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/portfolios-page/portfolios-page.component').then(m => m.PortfoliosPageComponent)
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./pages/portfolio-detail-page/portfolio-detail-page.component').then(m => m.PortfolioDetailPageComponent)
  }
];
