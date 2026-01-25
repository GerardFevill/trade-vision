import { Pipe, PipeTransform } from '@angular/core';
import { formatTime, formatDate, formatDateTime } from '../utils/format.utils';

/**
 * Time duration formatting pipe
 * Usage: {{ seconds | appTime }}
 */
@Pipe({
  name: 'appTime',
  standalone: true
})
export class TimePipe implements PipeTransform {
  transform(seconds: number | null | undefined): string {
    return formatTime(seconds);
  }
}

/**
 * Date formatting pipe
 * Usage: {{ dateString | appDate }}
 */
@Pipe({
  name: 'appDate',
  standalone: true
})
export class DatePipe implements PipeTransform {
  transform(date: string | null | undefined): string {
    return formatDate(date);
  }
}

/**
 * DateTime formatting pipe
 * Usage: {{ date | appDateTime }}
 */
@Pipe({
  name: 'appDateTime',
  standalone: true
})
export class DateTimePipe implements PipeTransform {
  transform(date: Date | null): string {
    return formatDateTime(date);
  }
}
