'use client';

import { DateTimeRangePicker, type DateRange } from '@/components/ui/datetime-range-picker';
import { useLanguage, translate } from '@/hooks/use-language';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useCallback, useMemo, useState } from 'react';

interface DateRangePickerProps {
  startTime: string;
  endTime: string;
  onStartTimeChange: (value: string) => void;
  onEndTimeChange: (value: string) => void;
}

/**
 * DateRangePicker component using shadcn DateTimeRangePicker
 *
 * This component wraps the DateTimeRangePicker to maintain backward compatibility
 * with the existing API while providing the new UI/UX.
 * Changes are buffered and only applied when the user clicks Apply.
 */
export function DateRangePicker({
  startTime,
  endTime,
  onStartTimeChange,
  onEndTimeChange,
}: DateRangePickerProps) {
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
        params.delete('startTime');
        params.delete('endTime');
        router.push(`${pathname}?${params.toString()}`);
        return;
      }

      // Build URL params once with both start and end times
      const params = new URLSearchParams(searchParams?.toString());

      // Update start time
      if (range.from) {
        const isoString = range.from.toISOString();
        onStartTimeChange(isoString);
        params.set('startTime', isoString);
      } else {
        params.delete('startTime');
      }

      // Update end time
      if (range.to) {
        const isoString = range.to.toISOString();
        onEndTimeChange(isoString);
        params.set('endTime', isoString);
      } else {
        params.delete('endTime');
      }

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
      className="w-full md:w-[320px]"
    />
  );
}
