/**
 * Account-related data models
 */

export interface AccountInfo {
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  margin_level: number | null;
  profit: number;
  leverage: number;
  server: string;
  name: string;
  login: number;
  currency: string;
  trade_mode: string;
}

export interface AccountStats {
  balance: number;
  equity: number;
  profit: number;
  drawdown: number;
  drawdown_percent: number;
  initial_deposit: number;
  total_deposits: number;
  total_withdrawals: number;
  growth_percent: number;
  timestamp: string;
}

export interface AccountSummary {
  id: number;
  name: string;
  broker: string;
  server: string;
  balance: number;
  equity: number;
  profit: number;
  profit_percent: number;
  drawdown: number;
  trades: number;
  win_rate: number;
  currency: string;
  leverage: number;
  connected: boolean;
}

export interface ConnectionStatus {
  connected: boolean;
  server: string | null;
  account: number | null;
  name: string | null;
  company: string | null;
}
