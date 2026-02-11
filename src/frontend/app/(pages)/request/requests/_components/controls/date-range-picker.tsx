'use client';

import { DateTimeRangePicker, type DateRange } from '@/components/ui/datetime-range-picker';
import { useLanguage, translate } from '@/hooks/use-language';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useCallback, useMemo, useState } from 'react';

interface RequestsDateRangePickerProps {
  startTime: string;
  endTime: string;
  onStartTimeChange: (value: string) => void;
  onEndTimeChange: (value: string) => void;
}

/**
 * RequestsDateRangePicker component using shadcn DateTimeRangePicker
 *
 * This component wraps the DateTimeRangePicker to maintain backward compatibility
 * with the existing API while providing the new UI/UX with presets and time selection.
 * Changes are buffered and only applied when the user clicks Apply.
 */
export function RequestsDateRangePicker({
  startTime,
  endTime,
  onStartTimeChange,
  onEndTimeChange,
}: RequestsDateRangePickerProps) {
  const { t } = useLanguage();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Local pending state - changes are buffered here until Apply is clicked
  const [pendingRange, setPendingRange] = useState<DateRange | undefined>(undefined);

  // Convert ISO strings to Date objects for the DateTimeRangePicker
  const dateRange = useMemo<DateRange>(() => {
    return {
      from: startTime ? new Date(startTime) : undefined,
      to: endTime ? new Date(endTime) : undefined,
    };
  }, [startTime, endTime]);

  /**
   * Handle date range changes from the DateTimeRangePicker
   * Store changes in pending state instead of applying immediately
   */
  const handleDateRangeChange = useCallback(
    (range: DateRange | undefined) => {
      setPendingRange(range);
    },
    []
  );

  /**
   * Apply the pending changes to the URL and parent state
   */
  const handleApply = useCallback(
    (range: DateRange | undefined) => {
      if (!range) {
        // Clear filters
        onStartTimeChange('');
        onEndTimeChange('');

        // Update URL parameters
        const params = new URLSearchParams(searchParams?.toString());
        params.delete('from_date');
        params.delete('to_date');
        params.delete('page'); // Reset to page 1
        router.push(`${pathname}?${params.toString()}`);
        return;
      }

      // Build URL params once with both start and end times
      const params = new URLSearchParams(searchParams?.toString());

      // Update start time
      if (range.from) {
        const isoString = range.from.toISOString();
        onStartTimeChange(isoString);
        params.set('from_date', isoString);
      } else {
        params.delete('from_date');
      }

      // Update end time
      if (range.to) {
        const isoString = range.to.toISOString();
        onEndTimeChange(isoString);
        params.set('to_date', isoString);
      } else {
        params.delete('to_date');
      }

      // Reset to page 1 when filters change
      params.delete('page');

      // Single router push with both parameters
      router.push(`${pathname}?${params.toString()}`);

      // Clear pending state
      setPendingRange(undefined);
    },
    [onStartTimeChange, onEndTimeChange, router, pathname, searchParams]
  );

  /**
   * Translation function for date picker labels
   */
  const translateDatePicker = useCallback(
    (key: string) => {
      return translate(t, key) || key;
    },
    [t]
  );

  return (
    <DateTimeRangePicker
      dateRange={pendingRange ?? dateRange}
      onDateRangeChange={handleDateRangeChange}
      onApply={handleApply}
      placeholder={translateDatePicker('common.datePicker.placeholder')}
      showPresets={true}
      t={(key: string) => translateDatePicker(`common.${key}`)}
      className="w-full md:w-auto"
    />
  );
}
