import { AccountSummary } from './account.model';

export interface PortfolioAccountDetail {
  account_id: number;
  lot_factor: number;
  account: AccountSummary | null;
}

export interface PortfolioDetail {
  id: number;
  name: string;
  type: string;
  client: string;
  total_balance: number;
  total_equity: number;
  total_profit: number;
  account_count: number;
  accounts: PortfolioAccountDetail[];
  available_factors: number[];
  created_at: string;
  updated_at: string;
}

export interface AddAccountRequest {
  account_id: number;
  lot_factor: number;
}
