"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { Table } from "@tanstack/react-table";
import { Button } from "@/components/data-table";
import { useLanguage, translate } from "@/hooks/use-language";
import { clientApi } from "@/lib/http/axios-client";
import { toast } from "@/components/ui/custom-toast";

/**
 * Value formatter function type for custom column export formatting
 */
export type ValueFormatter<TData> = (
  value: unknown,
  row: TData,
  columnId: string,
  language: string
) => string;

interface ExportAllButtonProps<TData> {
  /** Table instance to get visible columns */
  table: Table<TData> | null;
  /** API endpoint to fetch all data from */
  apiEndpoint: string;
  /** Filter parameters to apply */
  filters: Record<string, string | undefined>;
  /** Filename for export (without page number) */
  filename?: string;
  /** Current page number (1-indexed) */
  currentPage?: number;
  /** Page size (number of records per page) */
  pageSize?: number;
  /** Optional map of column IDs to value formatter functions */
  valueFormatters?: Record<string, ValueFormatter<TData>>;
  /** Optional map of column IDs to translated header labels */
  headerLabels?: Record<string, string>;
}

export function ExportAllButton<TData extends Record<string, unknown>>({
  table,
  apiEndpoint,
  filters,
  filename = "export",
  currentPage = 1,
  pageSize = 10,
  valueFormatters,
  headerLabels,
}: ExportAllButtonProps<TData>) {
  const { t, language } = useLanguage();
  const [isExporting, setIsExporting] = useState(false);

  /**
   * Format a cell value for CSV export
   */
  const formatCellValue = (
    value: unknown,
    row: TData,
    columnId: string
  ): string => {
    // Use custom formatter if provided
    if (valueFormatters?.[columnId]) {
      const formatted = valueFormatters[columnId](value, row, columnId, language);
      // Escape commas and quotes in formatted value
      if (formatted.includes(",") || formatted.includes('"')) {
        return `"${formatted.replace(/"/g, '""')}"`;
      }
      return formatted;
    }

    // Handle null/undefined
    if (value === undefined || value === null) {
      return "";
    }

    // Handle arrays
    if (Array.isArray(value)) {
      const joined = value.join("; ");
      if (joined.includes(",")) {
        return `"${joined}"`;
      }
      return joined;
    }

    // Handle booleans
    if (typeof value === "boolean") {
      return value ? translate(t, 'common.yes') : translate(t, 'common.no');
    }

    // Handle strings with commas
    const strValue = String(value);
    if (strValue.includes(",") || strValue.includes('"')) {
      return `"${strValue.replace(/"/g, '""')}"`;
    }

    return strValue;
  };

  const handleExportAll = async () => {
    // Do nothing if table is not ready
    if (!table) {
      return;
    }

    setIsExporting(true);

    try {
      // Get visible columns preserving order
      const visibleColumns = table
        .getVisibleFlatColumns()
        .filter((col) => col.id !== "select" && col.id !== "actions");

      // Build query params for current page only
      const params = new URLSearchParams();

      // Add filters
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== "") {
          params.append(key, value);
        }
      });

      // Use actual pagination parameters to export current page only
      const skip = (currentPage - 1) * pageSize;
      params.append("skip", skip.toString());
      params.append("limit", pageSize.toString());

      const url = `${apiEndpoint}?${params.toString()}`;

      // Fetch all data
      const response = await clientApi.get<{ data: TData[]; total: number } | TData[]>(url);

      if (!response.ok) {
        throw new Error('error' in response ? response.error : "Failed to fetch data");
      }

      if (!response.data) {
        throw new Error("No data received from server");
      }

      // Handle both paginated and non-paginated responses
      let allData: TData[];
      if (Array.isArray(response.data)) {
        // Direct array response (backward compatibility)
        allData = response.data;
      } else if (response.data && 'data' in response.data && Array.isArray(response.data.data)) {
        // Paginated response with data property
        allData = response.data.data;
      } else {
        throw new Error("Unexpected response format");
      }

      if (allData.length === 0) {
        // No data to export
        toast.error(translate(t, 'table.noDataToExport') || "No data to export on this page");
        return;
      }

      // Compose CSV header row from visible column headers
      // Priority: headerLabels prop > column header string > column id
      const headerRow = visibleColumns
        .map((col) => {
          if (headerLabels?.[col.id]) {
            return headerLabels[col.id];
          }
          if (typeof col.columnDef.header === "string") {
            return col.columnDef.header;
          }
          return col.id;
        })
        .join(",");

      // Compose CSV data rows from visible columns only
      const dataRows = allData.map((row) =>
        visibleColumns
          .map((col) => {
            const value = row[col.id];
            return formatCellValue(value, row, col.id);
          })
          .join(",")
      );

      const csvContent = [headerRow, ...dataRows].join("\n");

      // Trigger CSV file download with UTF-8 BOM for Excel compatibility
      const BOM = "\uFEFF";
      const blob = new Blob([BOM + csvContent], { type: "text/csv;charset=utf-8" });
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;

      // Generate filename with page number and record count
      const timestamp = new Date().toISOString().split('T')[0];
      a.download = `${filename}_page_${currentPage}_${timestamp}_${allData.length}records.csv`;

      a.click();
      window.URL.revokeObjectURL(downloadUrl);

      // Show success toast
      const successMessage = (translate(t, 'table.exportPageSuccess') ||
        translate(t, 'table.exportSuccess') ||
        `Successfully exported ${allData.length} records from page ${currentPage}`
      ).replace('{count}', String(allData.length)).replace('{page}', String(currentPage));
      toast.success(successMessage);

    } catch (error) {
      console.error("Export failed:", error);
      toast.error(
        translate(t, 'table.exportError') ||
        "Failed to export data. Please try again."
      );
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Button
      variant="default"
      size="default"
      onClick={handleExportAll}
      disabled={isExporting}
      icon={
        isExporting ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Download className="w-4 h-4" />
        )
      }
      tooltip={translate(t, 'table.exportPageTooltip') || translate(t, 'table.exportAllTooltip') || 'Export current page to CSV'}
    >
      {isExporting
        ? (translate(t, 'table.exporting') || "Exporting...")
        : (translate(t, 'table.exportPage') || translate(t, 'table.exportAll') || "Export Page")
      }
    </Button>
  );
}
