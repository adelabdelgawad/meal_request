"use client";

import React from "react";
import { Table } from "@tanstack/react-table";
import { DynamicTableBar } from "./data-table-bar";
import { SearchInput } from "../controls/search-input";
import { ExportButton, type ValueFormatter } from "../actions/export-button";
import { PrintButton } from "../actions/print-button";

export interface TableHeaderProps<TData> {
  /** Current page number for export/print */
  page: number;
  /** Table instance for export/print functionality */
  tableInstance: Table<TData> | null;
  /** Search placeholder text */
  searchPlaceholder?: string;
  /** URL param for search (default: "filter") */
  searchUrlParam?: string;
  /** Debounce time for search input (default: 500ms) */
  searchDebounceMs?: number;
  /** Filename for CSV export (default: "export") */
  exportFilename?: string;
  /** Title for print page */
  printTitle?: string;
  /** Whether to show export button (default: true) */
  showExport?: boolean;
  /** Whether to show print button (default: true) */
  showPrint?: boolean;
  /** Additional content to render on the left side */
  extraLeft?: React.ReactNode;
  /** Additional content to render on the right side */
  extraRight?: React.ReactNode;
  /** Custom value formatters for export (column ID -> formatter function) */
  exportValueFormatters?: Record<string, ValueFormatter<TData>>;
  /** Custom header labels for export (column ID -> label) */
  exportHeaderLabels?: Record<string, string>;
}

/**
 * Reusable table header component with search, export, and print controls.
 * Wraps DynamicTableBar with common table header functionality.
 */
export function TableHeader<TData>({
  page,
  tableInstance,
  searchPlaceholder = "Search...",
  searchUrlParam = "filter",
  searchDebounceMs = 500,
  exportFilename = "export",
  printTitle = "Data Table",
  showExport = true,
  showPrint = true,
  extraLeft,
  extraRight,
  exportValueFormatters,
  exportHeaderLabels,
}: TableHeaderProps<TData>) {
  return (
    <div className="shrink-0">
      <DynamicTableBar
        variant="header"
        left={
          <>
            <SearchInput
              placeholder={searchPlaceholder}
              urlParam={searchUrlParam}
              debounceMs={searchDebounceMs}
            />
            {extraLeft}
          </>
        }
        right={
          <>
            {extraRight}
            {showExport && (
              <ExportButton
                table={tableInstance}
                filename={exportFilename}
                page={page}
                valueFormatters={exportValueFormatters}
                headerLabels={exportHeaderLabels}
              />
            )}
            {showPrint && (
              <PrintButton
                table={tableInstance}
                title={printTitle}
                page={page}
              />
            )}
          </>
        }
      />
    </div>
  );
}
