import { Component, input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

export type SkeletonType = 'card' | 'text' | 'chart' | 'avatar' | 'badge' | 'custom';

@Component({
  selector: 'app-skeleton',
  standalone: true,
  imports: [CommonModule],
  template: `
    @switch (type()) {
      @case ('card') {
        <div class="skeleton skeleton-card" [style.height.px]="height()"></div>
      }
      @case ('text') {
        <div class="skeleton-text-container">
          @for (line of textLines(); track $index) {
            <div
              class="skeleton skeleton-text"
              [style.width.%]="line.width"
              [style.height.px]="line.height"
            ></div>
          }
        </div>
      }
      @case ('chart') {
        <div class="skeleton skeleton-chart" [style.height.px]="height() || 80"></div>
      }
      @case ('avatar') {
        <div class="skeleton skeleton-avatar" [style.width.px]="size()" [style.height.px]="size()"></div>
      }
      @case ('badge') {
        <div class="skeleton skeleton-badge"></div>
      }
      @case ('custom') {
        <div
          class="skeleton"
          [style.width]="width() ? width() + 'px' : '100%'"
          [style.height.px]="height()"
          [style.border-radius.px]="borderRadius()"
        ></div>
      }
    }
  `,
  styles: [`
    .skeleton {
      background: linear-gradient(
        90deg,
        #1a1a1a 25%,
        #252525 50%,
        #1a1a1a 75%
      );
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
    }

    @keyframes shimmer {
      0% {
        background-position: 200% 0;
      }
      100% {
        background-position: -200% 0;
      }
    }

    .skeleton-card {
      border-radius: 8px;
      min-height: 280px;
    }

    .skeleton-text-container {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .skeleton-text {
      height: 14px;
      border-radius: 4px;
    }

    .skeleton-chart {
      border-radius: 4px;
    }

    .skeleton-avatar {
      border-radius: 10px;
    }

    .skeleton-badge {
      width: 80px;
      height: 24px;
      border-radius: 12px;
    }
  `]
})
export class SkeletonComponent {
  type = input<SkeletonType>('custom');
  lines = input<number>(3);
  height = input<number>(0);
  width = input<number>(0);
  size = input<number>(48);
  borderRadius = input<number>(8);

  textLines = computed(() => {
    const count = this.lines();
    return Array.from({ length: count }, (_, i) => ({
      width: i === count - 1 ? 60 : 100, // Last line shorter
      height: 14
    }));
  });
}
