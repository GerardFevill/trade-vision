/**
 * Analytics and risk data models
 */

export interface RiskMetrics {
  max_drawdown: number;
  max_drawdown_percent: number;
  relative_drawdown_balance: number;
  relative_drawdown_equity: number;
  max_deposit_load: number;
  sharpe_ratio: number;
  recovery_factor: number;
  current_drawdown: number;
  current_drawdown_percent: number;
}

export interface HistoryPoint {
  balance: number;
  equity: number;
  drawdown: number;
  drawdown_percent: number;
  timestamp: string;
}

export interface DailyDrawdown {
  date: string;
  drawdown_percent: number;
  start_balance: number;
  min_balance: number;
}

export interface MonthlyGrowth {
  year: number;
  months: Record<string, number | null>;
  values: Record<string, number | null>;
  year_total: number | null;
  year_total_value: number | null;
}

export interface GlobalMonthlyGrowthMonth {
  profit_eur: number;
  profit_usd: number;
}

export interface GlobalMonthlyGrowth {
  year: number;
  months: Record<string, GlobalMonthlyGrowthMonth | null>;
  year_total_eur: number;
  year_total_usd: number;
}

export type SparklineData = Record<number, number[]>;
