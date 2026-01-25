import { Component, input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

export type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral';
export type BadgeSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'app-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span
      class="badge"
      [class]="badgeClasses()"
    >
      @if (icon()) {
        <i [class]="'fa fa-' + icon()"></i>
      }
      <ng-content></ng-content>
    </span>
  `,
  styles: [`
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
      border-radius: 20px;
      white-space: nowrap;
      transition: all 0.2s ease;

      i {
        font-size: 0.85em;
      }
    }

    // Sizes
    .badge-sm {
      font-size: 10px;
      padding: 2px 8px;
    }

    .badge-md {
      font-size: 11px;
      padding: 4px 10px;
    }

    .badge-lg {
      font-size: 12px;
      padding: 6px 14px;
    }

    // Variants
    .badge-success {
      color: #22c55e;
      background: rgba(34, 197, 94, 0.15);
      border: 1px solid rgba(34, 197, 94, 0.3);
    }

    .badge-warning {
      color: #f59e0b;
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .badge-danger {
      color: #ef4444;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .badge-info {
      color: #3b82f6;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
    }

    .badge-neutral {
      color: #888888;
      background: rgba(136, 136, 136, 0.15);
      border: 1px solid rgba(136, 136, 136, 0.3);
    }

    // Pill variant (more rounded)
    .badge-pill {
      border-radius: 100px;
    }

    // Outline variant
    .badge-outline {
      background: transparent;
    }

    // Dot indicator
    .badge-dot {
      &::before {
        content: '';
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: currentColor;
      }
    }
  `]
})
export class BadgeComponent {
  variant = input<BadgeVariant>('neutral');
  size = input<BadgeSize>('md');
  icon = input<string>('');
  pill = input<boolean>(false);
  outline = input<boolean>(false);
  dot = input<boolean>(false);

  badgeClasses = computed(() => {
    const classes = [
      `badge-${this.variant()}`,
      `badge-${this.size()}`
    ];

    if (this.pill()) classes.push('badge-pill');
    if (this.outline()) classes.push('badge-outline');
    if (this.dot()) classes.push('badge-dot');

    return classes.join(' ');
  });
}
