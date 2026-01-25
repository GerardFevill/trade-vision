import { Pipe, PipeTransform } from '@angular/core';
import { formatPercent, formatPercentSigned } from '../utils/format.utils';

/**
 * Percentage formatting pipe
 * Usage: {{ value | appPercent }} or {{ value | appPercent:true }} for signed
 */
@Pipe({
  name: 'appPercent',
  standalone: true
})
export class PercentPipe implements PipeTransform {
  transform(value: number | null | undefined, signed = false): string {
    return signed ? formatPercentSigned(value) : formatPercent(value);
  }
}
