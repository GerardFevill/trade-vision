import { Component, input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

export type TrendDirection = 'up' | 'down' | 'neutral';

@Component({
  selector: 'app-stat-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="stat-card" [class.stat-card-compact]="compact()">
      <span class="stat-label">{{ label() }}</span>
      <span class="stat-value" [class]="valueClass()">
        @if (showTrendIcon() && trend() !== 'neutral') {
          <i class="fa" [class.fa-arrow-up]="trend() === 'up'" [class.fa-arrow-down]="trend() === 'down'"></i>
        }
        {{ value() }}
      </span>
      @if (subtitle()) {
        <span class="stat-subtitle">{{ subtitle() }}</span>
      }
    </div>
  `,
  styles: [`
    .stat-card {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 12px 16px;
      background: rgba(26, 26, 26, 0.5);
      border-radius: 8px;
      transition: all 0.2s ease;

      &:hover {
        background: rgba(26, 26, 26, 0.8);
      }
    }

    .stat-card-compact {
      padding: 8px 12px;
      gap: 2px;
    }

    .stat-label {
      font-size: 10px;
      color: #555555;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 500;
    }

    .stat-value {
      font-size: 15px;
      font-weight: 600;
      color: #e0e0e0;
      display: flex;
      align-items: center;
      gap: 4px;

      i {
        font-size: 10px;
      }
    }

    .stat-subtitle {
      font-size: 11px;
      color: #888888;
    }

    // Trend colors
    .trend-up {
      color: #22c55e !important;
    }

    .trend-down {
      color: #ef4444 !important;
    }

    .trend-neutral {
      color: #888888 !important;
    }

    // Accent colors
    .accent-primary {
      color: #3b82f6 !important;
    }

    .accent-warning {
      color: #f59e0b !important;
    }
  `]
})
export class StatCardComponent {
  label = input.required<string>();
  value = input.required<string>();
  trend = input<TrendDirection>('neutral');
  subtitle = input<string>('');
  compact = input<boolean>(false);
  showTrendIcon = input<boolean>(true);
  accentColor = input<'primary' | 'warning' | ''>('');

  valueClass = computed(() => {
    const classes: string[] = [];

    if (this.trend() !== 'neutral') {
      classes.push(`trend-${this.trend()}`);
    }

    if (this.accentColor()) {
      classes.push(`accent-${this.accentColor()}`);
    }

    return classes.join(' ');
  });
}
