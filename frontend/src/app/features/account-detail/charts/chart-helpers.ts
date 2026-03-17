import { HistoryPoint } from '@app/data-access';

export type Timeframe = '1H' | '1D' | '1W' | '1M' | '1Y' | 'All';
export type ChartMode = 'all' | 'growth' | 'drawdown';

const TIMEFRAME_MINUTES: Record<Timeframe, number> = {
  '1H': 60, '1D': 1440, '1W': 10080, '1M': 43200, '1Y': 525600, 'All': Infinity
};

export function filterHistoryByTimeframe(history: HistoryPoint[], tf: Timeframe): HistoryPoint[] {
  if (tf === 'All') return history;

  const minutes = TIMEFRAME_MINUTES[tf];
  const cutoff = new Date(Date.now() - minutes * 60 * 1000);
  const filtered = history.filter(h => new Date(h.timestamp) >= cutoff);
  return filtered.length === 0 ? history : filtered;
}

export function getTimeframeFormatOptions(tf: Timeframe): Intl.DateTimeFormatOptions {
  if (tf === '1H') return { hour: '2-digit', minute: '2-digit' };
  if (tf === '1D' || tf === '1W') return { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' };
  return { day: '2-digit', month: '2-digit', year: '2-digit' };
}
