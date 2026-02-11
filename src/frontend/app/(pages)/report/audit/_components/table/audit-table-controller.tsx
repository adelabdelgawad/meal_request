"use client";

import { DynamicTableBar } from "@/components/data-table/table/data-table-bar";
import { SearchInput } from "@/components/data-table/controls/search-input";
import { DateRangePicker } from "@/app/(pages)/report/analysis/_components/controls/date-range-picker";
import { RefreshButton } from "@/components/data-table/controls/refresh-button";
import { ColumnToggleButton } from "@/components/data-table/controls/column-toggle-button";
import { ExportAllAuditButton } from "../actions/export-all-audit-button";
import { PrintAllAuditButton } from "../actions/print-all-audit-button";
import { useLanguage, translate } from "@/hooks/use-language";
import type { AuditRecord } from "@/types/analytics.types";

interface AuditTableControllerProps {
  onRefresh: () => void;
  tableInstance: import("@tanstack/react-table").Table<AuditRecord> | null;
  // Date range filter props
  startTime: string;
  endTime: string;
  onStartTimeChange: (value: string) => void;
  onEndTimeChange: (value: string) => void;
  /** Search filter */
  search?: string;
  /** Map of column IDs to translated labels for column toggle menu */
  columnLabels?: Record<string, string>;
}

/**
 * Controller section of the audit table with search, date filters, and action buttons
 */
export function AuditTableController({
  onRefresh,
  tableInstance,
  startTime,
  endTime,
  onStartTimeChange,
  onEndTimeChange,
  search,
  columnLabels,
}: AuditTableControllerProps) {
  const { t } = useLanguage();

  return (
    <div className="shrink-0">
      <DynamicTableBar
        variant="controller"
        left={
          <SearchInput
            placeholder={
              translate(t, "audit.searchPlaceholder") ||
              "Search audit records..."
            }
            urlParam="search"
            debounceMs={500}
          />
        }
        right={
          <>
            <DateRangePicker
              startTime={startTime}
              endTime={endTime}
              onStartTimeChange={onStartTimeChange}
              onEndTimeChange={onEndTimeChange}
            />
            <RefreshButton onRefresh={onRefresh} />
            <ColumnToggleButton
              table={tableInstance}
              columnLabels={columnLabels}
            />
            <ExportAllAuditButton
              table={tableInstance}
              startTime={startTime}
              endTime={endTime}
              search={search}
            />
            <PrintAllAuditButton
              table={tableInstance}
              startTime={startTime}
              endTime={endTime}
              search={search}
            />
          </>
        }
      />
    </div>
  );
}
