/**
 * Dashboard composite data model
 */

import { AccountInfo, AccountStats } from './account.model';
import { TradeStats, Position } from './trade.model';
import { RiskMetrics, MonthlyGrowth } from './analytics.model';

export interface FullDashboard {
  account: AccountInfo;
  stats: AccountStats;
  trade_stats: TradeStats;
  risk_metrics: RiskMetrics;
  open_positions: Position[];
  monthly_growth: MonthlyGrowth[];
}
