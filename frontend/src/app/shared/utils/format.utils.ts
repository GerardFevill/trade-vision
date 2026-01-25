/**
 * Shared formatting utilities
 * Pure functions for data transformation
 */

export function formatNumber(val: number | null | undefined, decimals = 2): string {
  return val != null ? val.toFixed(decimals) : '-';
}

export function formatCurrency(val: number | null | undefined, currency = 'EUR'): string {
  if (val == null) return '-';
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency }).format(val);
}

export function formatPercent(val: number | null | undefined): string {
  return val != null ? val.toFixed(2) + '%' : '-';
}

export function formatPercentSigned(val: number | null | undefined): string {
  if (val == null) return '-';
  const sign = val >= 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
}

export function formatTime(seconds: number | null | undefined): string {
  if (!seconds) return '-';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return '-';
  return new Date(date).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export function formatDateTime(date: Date | null): string {
  if (!date) return '-';
  return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

// CSS Class helpers
export function getProfitClass(val: number | null | undefined): string {
  if (val == null) return '';
  return val >= 0 ? 'positive' : 'negative';
}

export function getDrawdownClass(val: number | null | undefined): string {
  if (val == null) return '';
  if (val >= 50) return 'dd-critical';
  if (val >= 30) return 'dd-warning';
  if (val >= 10) return 'dd-moderate';
  return 'dd-low';
}

export function getPerformanceClass(profitPercent: number): string {
  if (profitPercent >= 50) return 'perf-excellent';
  if (profitPercent >= 20) return 'perf-good';
  if (profitPercent >= 0) return 'perf-neutral';
  if (profitPercent >= -20) return 'perf-warning';
  return 'perf-danger';
}

export function getBarPercent(value: number | null | undefined, max: number | null | undefined): number {
  if (!value || !max || max === 0) return 0;
  return Math.min(Math.max((value / max) * 100, 0), 100);
}
