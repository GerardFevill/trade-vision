/**
 * Portfolio-related data models
 */

import { AccountSummary } from './account.model';

export type PortfolioType = 'Securise' | 'Conservateur' | 'Modere' | 'Agressif';

export const PORTFOLIO_TYPES: Record<PortfolioType, number[]> = {
  Securise: [],  // Pas de facteur - nombre illimite de comptes
  Conservateur: [0.2, 0.6, 1.0, 1.4, 1.8],
  Modere: [2.0],
  Agressif: [2.5, 3.0, 3.5, 4.0, 4.5],
};

export const LOT_FACTORS = [0.2, 0.6, 1.0, 1.4, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5];

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
  created_at: string;
  updated_at: string;
}

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

export interface CreatePortfolioRequest {
  name: string;
  type: PortfolioType;
  client: string;
}

export interface UpdatePortfolioRequest {
  name?: string;
  type?: PortfolioType;
}

export interface AddAccountRequest {
  account_id: number;
  lot_factor: number;
}

// Monthly record models
export interface MonthlyAccountRecord {
  account_id: number;
  account_name: string;
  lot_factor: number;
  starting_balance: number;
  ending_balance: number;
  profit: number;
  profit_percent: number;
  weight: number;
  suggested_withdrawal: number;
  actual_withdrawal: number;
  currency: string;
}

export interface MonthlySnapshot {
  month: string;
  total_starting: number;
  total_ending: number;
  total_profit: number;
  total_profit_percent: number;
  total_withdrawal: number;
  accounts: MonthlyAccountRecord[];
  is_closed: boolean;
}

// Elite level system types
export type EliteLevel = 'N5' | 'N4' | 'N3' | 'N2' | 'N1';

export interface EliteTransfer {
  from_level: EliteLevel;
  to_level: EliteLevel;
  amount: number;
  from_account: string;
  from_account_id: number;
  to_account: string;
  to_account_id?: number;
}

export interface EliteAccountPreview {
  account_id: number;
  account_name: string;
  lot_factor: number;
  level: EliteLevel;
  starting_balance: number;
  current_balance: number;
  monthly_profit: number;
  profit_percent: number;
  remuneration: number;
  remuneration_pct: number;
  compound: number;
  compound_pct: number;
  transfer: number;
  transfer_pct: number;
  currency: string;
}

export interface StandardAccountPreview {
  account_id: number;
  account_name: string;
  lot_factor: number;
  starting_balance: number;
  current_balance: number;
  monthly_profit: number;
  profit_percent: number;
  weight: number;
  suggested_withdrawal: number;
  currency: string;
}

export interface CurrentMonthPreview {
  month: string;
  month_start: string;
  current_date: string;
  days_elapsed: number;
  days_in_month: number;
  portfolio_type: string;
  is_elite: boolean;
  total_starting: number;
  total_current: number;
  total_profit: number;
  total_profit_percent: number;

  // Standard system (Modere, Agressif)
  withdrawal_percentage?: number;
  total_suggested_withdrawal?: number;
  accounts?: StandardAccountPreview[];

  // Elite system (Conservateur)
  phase?: number;
  phase_name?: string;
  phase_thresholds?: string;
  total_remuneration?: number;
  total_compound?: number;
  total_transfer?: number;
  transfers?: EliteTransfer[];
  elite_accounts?: EliteAccountPreview[];
}

export interface UpdateWithdrawalRequest {
  account_id: number;
  withdrawal: number;
  note?: string;
}

// Withdrawal percentages by type
export const WITHDRAWAL_PERCENTAGES: Record<string, number> = {
  Securise: 50,
  Conservateur: 70,
  Modere: 80,
  Agressif: 90,
};
