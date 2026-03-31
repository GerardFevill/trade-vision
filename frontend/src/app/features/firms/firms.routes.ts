import { Routes } from '@angular/router';

export const FIRMS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/firms-page/firms-page.component').then(m => m.FirmsPageComponent)
  }
];
