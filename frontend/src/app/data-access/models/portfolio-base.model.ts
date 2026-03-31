import { PortfolioType } from './portfolio.constants';

export interface CurrencyBalance {
  currency: string;
  balance: number;
  profit: number;
}

export interface Portfolio {
  id: number;
  name: string;
  type: PortfolioType;
  client: string;
  created_at: string;
  updated_at: string;
}

export interface PortfolioSummary {
  id: number;
  name: string;
  type: string;
  client: string;
  total_balance: number;
  total_profit: number;
  account_count: number;
  balances_by_currency: CurrencyBalance[];
  created_at: string;
  updated_at: string;
}

export interface CreatePortfolioRequest {
  name: string;
  type: PortfolioType;
  client: string;
}

export interface UpdatePortfolioRequest {
  name?: string;
  type?: PortfolioType;
}
