import { Pipe, PipeTransform } from '@angular/core';
import { formatCurrency } from '../utils/format.utils';

/**
 * Currency formatting pipe
 * Usage: {{ value | appCurrency:'EUR' }}
 */
@Pipe({
  name: 'appCurrency',
  standalone: true
})
export class CurrencyPipe implements PipeTransform {
  transform(value: number | null | undefined, currency = 'EUR'): string {
    return formatCurrency(value, currency);
  }
}
