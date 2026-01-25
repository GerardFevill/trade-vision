import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartType } from 'chart.js';

@Component({
  selector: 'app-sparkline',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  template: `
    <div class="sparkline-wrapper" [style.height.px]="height">
      <canvas baseChart
        [type]="chartType"
        [data]="chartData"
        [options]="chartOptions">
      </canvas>
    </div>
  `,
  styles: [`
    .sparkline-wrapper {
      width: 100%;
      position: relative;
    }
    canvas {
      width: 100% !important;
      height: 100% !important;
    }
  `]
})
export class SparklineComponent implements OnChanges {
  @Input() data: number[] = [];
  @Input() height: number = 60;
  @Input() color: string = '#22c55e';
  @Input() fillColor: string = 'rgba(34, 197, 94, 0.2)';
  @Input() showFill: boolean = true;

  chartType: ChartType = 'line';
  chartData: ChartConfiguration['data'] = { labels: [], datasets: [] };
  chartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false }
    },
    scales: {
      x: { display: false },
      y: { display: false }
    },
    elements: {
      point: { radius: 0 },
      line: { tension: 0.4, borderWidth: 2 }
    }
  };

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data'] || changes['color'] || changes['fillColor']) {
      this.updateChart();
    }
  }

  private updateChart(): void {
    if (!this.data || this.data.length < 2) {
      this.chartData = { labels: [], datasets: [] };
      return;
    }

    // Determine color based on trend (if not explicitly set)
    const trendColor = this.data[this.data.length - 1] >= this.data[0]
      ? this.color
      : '#ef4444';

    const trendFill = this.data[this.data.length - 1] >= this.data[0]
      ? this.fillColor
      : 'rgba(239, 68, 68, 0.2)';

    this.chartData = {
      labels: this.data.map(() => ''),
      datasets: [{
        data: this.data,
        borderColor: trendColor,
        backgroundColor: this.showFill ? trendFill : 'transparent',
        fill: this.showFill,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0
      }]
    };
  }
}
