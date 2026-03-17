import { ChartConfiguration } from 'chart.js';
import { DailyDrawdown } from '@app/data-access';

export const DRAWDOWN_CHART_OPTIONS: ChartConfiguration['options'] = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { intersect: false, mode: 'index' },
  plugins: {
    legend: { display: false },
    tooltip: { backgroundColor: '#1a1a1a', titleColor: '#fff', bodyColor: '#aaa', borderColor: '#333', borderWidth: 1 }
  },
  scales: {
    x: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 12 } },
    y: { grid: { color: '#1f1f1f' }, ticks: { color: '#666', font: { size: 10 } }, reverse: true }
  }
};

export function buildDrawdownChartData(daily: DailyDrawdown[]): ChartConfiguration['data'] {
  return {
    labels: daily.map(d => d.date),
    datasets: [{
      label: 'Drawdown %',
      data: daily.map(d => d.drawdown_percent),
      borderColor: '#ef4444',
      backgroundColor: 'rgba(239,68,68,0.2)',
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 2
    }]
  };
}
