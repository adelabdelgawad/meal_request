'use client';

import { LiveIndicator } from '../../requests/_components/live-indicator';
import { DateRangePicker } from '../../analysis/_components/controls/date-range-picker';

interface HistoryFiltersProps {
  fromDate: string;
  toDate: string;
  isLive: boolean;
  isValidating?: boolean;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
}

export function HistoryFilters({
  fromDate,
  toDate,
  isLive,
  isValidating = false,
  onFromDateChange,
  onToDateChange,
}: HistoryFiltersProps) {
  return (
    <div className="bg-card rounded-lg border shadow-sm p-4">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        {/* Date Range Picker */}
        <DateRangePicker
          startTime={fromDate}
          endTime={toDate}
          onStartTimeChange={onFromDateChange}
          onEndTimeChange={onToDateChange}
        />

        {/* Spacer */}
        <div className="flex-1" />

        {/* Status and Actions - Always on the right */}
        <div className="flex items-center gap-2">
          <LiveIndicator isLive={isLive} isValidating={isValidating} />
        </div>
      </div>
    </div>
  );
}
