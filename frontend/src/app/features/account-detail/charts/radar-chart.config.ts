import { ChartConfiguration } from 'chart.js';

export const RADAR_OPTIONS: ChartConfiguration<'radar'>['options'] = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: { legend: { display: false } },
  scales: {
    r: {
      angleLines: { color: '#2a2a2a' },
      grid: { color: '#2a2a2a' },
      pointLabels: { color: '#888', font: { size: 10 } },
      ticks: { display: false, stepSize: 20 },
      min: 0,
      max: 100
    }
  }
};

export const RADAR_LABELS = ['Algo trading', 'Bénéfice trades', 'Perte trades', 'Activité', 'Charge dépôt', 'Prélèvement max'];

export function buildRadarData(
  tradeStats: { win_rate: number; total_trades: number },
  riskMetrics: { max_deposit_load: number; max_drawdown_percent: number }
): ChartConfiguration<'radar'>['data'] {
  return {
    labels: RADAR_LABELS,
    datasets: [{
      data: [
        98,
        Math.min(tradeStats.win_rate, 100),
        100 - Math.min(tradeStats.win_rate, 100),
        Math.min((tradeStats.total_trades / 500) * 100, 100),
        Math.min(riskMetrics.max_deposit_load, 100),
        Math.min(riskMetrics.max_drawdown_percent, 100)
      ],
      backgroundColor: 'rgba(59, 130, 246, 0.2)',
      borderColor: '#3b82f6',
      borderWidth: 2,
      pointBackgroundColor: '#3b82f6'
    }]
  };
}
