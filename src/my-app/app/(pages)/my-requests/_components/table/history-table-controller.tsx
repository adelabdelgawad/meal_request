"use client";

import { DynamicTableBar } from "@/components/data-table/table/data-table-bar";
import { DateRangePicker } from "@/app/(pages)/analysis/_components/controls/date-range-picker";
import { LiveIndicator } from "@/app/(pages)/requests/_components/live-indicator";

interface HistoryTableControllerProps {
  fromDate: string;
  toDate: string;
  isLive: boolean;
  isValidating?: boolean;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
}

/**
 * Controller section for the my-requests table with date filters and live indicator
 */
export function HistoryTableController({
  fromDate,
  toDate,
  isLive,
  isValidating = false,
  onFromDateChange,
  onToDateChange,
}: HistoryTableControllerProps) {
  return (
    <div className="shrink-0">
      <DynamicTableBar
        variant="controller"
        left={
          <DateRangePicker
            startTime={fromDate}
            endTime={toDate}
            onStartTimeChange={onFromDateChange}
            onEndTimeChange={onToDateChange}
          />
        }
        right={
          <LiveIndicator isLive={isLive} isValidating={isValidating} />
        }
      />
    </div>
  );
}
