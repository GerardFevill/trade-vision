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
