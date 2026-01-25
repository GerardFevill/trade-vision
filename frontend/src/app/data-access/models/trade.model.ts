/**
 * Trade-related data models
 */

export interface Trade {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  open_time: string;
  open_price: number;
  close_time: string | null;
  close_price: number | null;
  profit: number;
  commission: number;
  swap: number;
  comment: string;
}

export interface Position {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  open_time: string;
  open_price: number;
  current_price: number;
  profit: number;
  sl: number | null;
  tp: number | null;
}

export interface TradeStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  best_trade: number;
  worst_trade: number;
  gross_profit: number;
  gross_loss: number;
  profit_factor: number;
  average_profit: number;
  average_loss: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  longs_count: number;
  shorts_count: number;
  longs_won: number;
  shorts_won: number;
  avg_holding_time_seconds: number;
  expected_payoff: number;
}
