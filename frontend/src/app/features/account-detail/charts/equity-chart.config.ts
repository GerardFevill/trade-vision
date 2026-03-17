import { ChartConfiguration, ChartType } from 'chart.js';
import { HistoryPoint } from '@app/data-access';
import { ChartMode, Timeframe, filterHistoryByTimeframe, getTimeframeFormatOptions } from './chart-helpers';

export const EQUITY_CHART_TYPE: ChartType = 'line';

export const EQUITY_CHART_OPTIONS: ChartConfiguration['options'] = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { intersect: false, mode: 'index' },
  plugins: {
    legend: { display: true, position: 'top', labels: { color: '#888', font: { size: 11 } } },
    tooltip: { backgroundColor: '#1a1a1a', titleColor: '#fff', bodyColor: '#aaa', borderColor: '#333', borderWidth: 1 }
  },
  scales: {
    x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 10 } },
    y: { type: 'linear', position: 'left', grid: { color: '#1f1f1f' }, ticks: { color: '#22c55e', font: { size: 10 } } },
    y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#f59e0b', font: { size: 10 } }, reverse: true }
  }
};

export function buildEquityChartData(
  history: HistoryPoint[],
  tf: Timeframe,
  mode: ChartMode
): { data: ChartConfiguration['data']; options: ChartConfiguration['options'] } {
  const filtered = filterHistoryByTimeframe(history, tf);
  if (!filtered.length) return { data: { labels: [], datasets: [] }, options: EQUITY_CHART_OPTIONS };

  const formatOptions = getTimeframeFormatOptions(tf);
  const labels = filtered.map(h => new Date(h.timestamp).toLocaleString('fr-FR', formatOptions));

  if (mode === 'all') {
    return {
      options: {
        ...EQUITY_CHART_OPTIONS,
        scales: {
          x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 10 } },
          y: { type: 'linear', position: 'left', grid: { color: '#1f1f1f' }, ticks: { color: '#22c55e', font: { size: 10 } } },
          y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#f59e0b', font: { size: 10 } }, reverse: true }
        }
      },
      data: {
        labels,
        datasets: [
          { label: 'Solde', data: filtered.map(h => h.balance), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2, yAxisID: 'y' },
          { label: 'Prélèvement %', data: filtered.map(h => h.drawdown_percent), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2, yAxisID: 'y1' }
        ]
      }
    };
  }

  if (mode === 'growth') {
    return {
      options: {
        ...EQUITY_CHART_OPTIONS,
        scales: {
          x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 10 } },
          y: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 } } }
        }
      },
      data: {
        labels,
        datasets: [
          { label: 'Solde', data: filtered.map(h => h.balance), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 },
          { label: 'Fonds propres', data: filtered.map(h => h.equity), borderColor: '#3b82f6', backgroundColor: 'transparent', fill: false, tension: 0.3, pointRadius: 0, borderWidth: 2 }
        ]
      }
    };
  }

  // drawdown mode
  return {
    options: {
      ...EQUITY_CHART_OPTIONS,
      scales: {
        x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 10 } },
        y: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 } }, reverse: true }
      }
    },
    data: {
      labels,
      datasets: [{ label: 'Prélèvement', data: filtered.map(h => h.drawdown_percent), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 }]
    }
  };
}
