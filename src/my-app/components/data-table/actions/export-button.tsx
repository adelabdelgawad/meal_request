"use client";

import { Download } from "lucide-react";
import { Table } from "@tanstack/react-table";
import { Button } from "@/components/data-table";
import { useLanguage, translate } from "@/hooks/use-language";

/**
 * Value formatter function type for custom column export formatting
 */
export type ValueFormatter<TData> = (
  value: unknown,
  row: TData,
  columnId: string,
  language: string
) => string;

interface ExportButtonProps<TData> {
  table: Table<TData> | null;
  filename?: string;
  page?: number;
  /** Optional map of column IDs to value formatter functions */
  valueFormatters?: Record<string, ValueFormatter<TData>>;
  /** Optional map of column IDs to translated header labels */
  headerLabels?: Record<string, string>;
}

export function ExportButton<TData>({
  table,
  filename = "export",
  page = 1,
  valueFormatters,
  headerLabels,
}: ExportButtonProps<TData>) {
  const { t, language } = useLanguage();

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

    // Handle arrays (like roleIds)
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

  const handleExport = () => {
    // Do nothing if table is not ready
    if (!table) {
      return;
    }
    // Get visible columns preserving order
    const visibleColumns = table
      .getVisibleFlatColumns()
      .filter((col) => col.id !== "select" && col.id !== "actions");

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

    // Compose CSV data rows from table rows and visible columns
    const dataRows = table.getRowModel().rows.map((row) =>
      visibleColumns
        .map((col) => {
          const value = row.getValue(col.id);
          return formatCellValue(value, row.original, col.id);
        })
        .join(",")
    );

    const csvContent = [headerRow, ...dataRows].join("\n");

    // Trigger CSV file download with UTF-8 BOM for Excel compatibility
    const BOM = "\uFEFF";
    const blob = new Blob([BOM + csvContent], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}_page_${page}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <>
      <Button
        variant="default"
        size="default"
        onClick={handleExport}
        icon={<Download className="w-4 h-4" />}
        tooltip={translate(t, 'table.exportTooltip')}
      >
        {translate(t, 'table.export')}
      </Button>
    </>
  );
}
