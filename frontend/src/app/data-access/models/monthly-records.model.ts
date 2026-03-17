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

export interface UpdateWithdrawalRequest {
  account_id: number;
  withdrawal: number;
  note?: string;
}
