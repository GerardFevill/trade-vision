import { Component, input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartType, Chart, CategoryScale, LinearScale, LineController, LineElement, PointElement, Filler } from 'chart.js';

// Register Chart.js components
Chart.register(CategoryScale, LinearScale, LineController, LineElement, PointElement, Filler);

/**
 * Reusable sparkline chart component
 * Displays a mini trend line based on array of values
 */
@Component({
  selector: 'app-sparkline',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  template: `
    <div class="sparkline-wrapper" [style.height.px]="height()">
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
  data = input<number[]>([]);
  height = input<number>(60);
  color = input<string>('#22c55e');
  fillColor = input<string>('rgba(34, 197, 94, 0.2)');
  showFill = input<boolean>(true);

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
    const dataValues = this.data();
    if (!dataValues || dataValues.length < 2) {
      this.chartData = { labels: [], datasets: [] };
      return;
    }

    const trendColor = dataValues[dataValues.length - 1] >= dataValues[0]
      ? this.color()
      : '#ef4444';

    const trendFill = dataValues[dataValues.length - 1] >= dataValues[0]
      ? this.fillColor()
      : 'rgba(239, 68, 68, 0.2)';

    this.chartData = {
      labels: dataValues.map(() => ''),
      datasets: [{
        data: dataValues,
        borderColor: trendColor,
        backgroundColor: this.showFill() ? trendFill : 'transparent',
        fill: this.showFill(),
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0
      }]
    };
  }
}
