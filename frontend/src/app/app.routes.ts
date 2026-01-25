import { Routes } from '@angular/router';
import { AccountsListComponent } from './components/accounts-list/accounts-list.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';

export const routes: Routes = [
  { path: '', redirectTo: '/accounts', pathMatch: 'full' },
  { path: 'accounts', component: AccountsListComponent },
  { path: 'dashboard/:id', component: DashboardComponent },
];
