"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { Table } from "@tanstack/react-table";
import { Button } from "@/components/data-table";
import { useLanguage, translate } from "@/hooks/use-language";
import { clientApi } from "@/lib/http/axios-client";
import { toast } from "@/components/ui/custom-toast";
import type { AuditRecord } from "@/types/analytics.types";

interface ExportAllAuditButtonProps {
  /** Table instance to get visible columns */
  table: Table<AuditRecord> | null;
  /** Start time filter */
  startTime: string;
  /** End time filter */
  endTime: string;
  /** Search filter */
  search?: string;
  /** Filename for export */
  filename?: string;
}

export function ExportAllAuditButton({
  table,
  startTime,
  endTime,
  search,
  filename = "audit_report",
}: ExportAllAuditButtonProps) {
  const { t, language } = useLanguage();
  const [isExporting, setIsExporting] = useState(false);

  /**
   * Format a cell value for CSV export
   */
  const formatCellValue = (value: unknown, columnId: string): string => {
    // Handle null/undefined
    if (value === undefined || value === null) {
      return "";
    }

    // Handle booleans
    if (typeof value === "boolean") {
      return value ? translate(t, "common.yes") : translate(t, "common.no");
    }

    // Handle dates
    if (value instanceof Date) {
      return value.toLocaleString(language === "ar" ? "ar-SA" : "en-US");
    }

    // Handle strings with commas or quotes
    const strValue = String(value);
    if (strValue.includes(",") || strValue.includes('"')) {
      return `"${strValue.replace(/"/g, '""')}"`;
    }

    return strValue;
  };

  /**
   * Get localized header for a column
   */
  const getColumnHeader = (columnId: string): string => {
    const headerMap: Record<string, string> = {
      code: translate(t, "audit.columns.code") || "Code",
      employeeName:
        translate(t, "audit.columns.name") || "Employee Name",
      title: translate(t, "audit.columns.title") || "Title",
      department:
        translate(t, "audit.columns.department") || "Department",
      requester: translate(t, "audit.columns.requester") || "Requester",
      requesterTitle:
        translate(t, "audit.columns.requesterTitle") ||
        "Requester Title",
      requestTime:
        translate(t, "audit.columns.requestTime") || "Request Time",
      mealType: translate(t, "audit.columns.mealType") || "Meal Type",
      inTime:
        translate(t, "audit.columns.attendanceIn") || "Attendance In",
      outTime:
        translate(t, "audit.columns.attendanceOut") || "Attendance Out",
      workingHours: translate(t, "audit.columns.hours") || "Working Hours",
      notes: translate(t, "audit.columns.notes") || "Notes",
    };

    return headerMap[columnId] || columnId;
  };

  /**
   * Get the appropriate value for bilingual fields based on current language
   */
  const getBilingualValue = (
    record: AuditRecord,
    fieldPrefix: string
  ): string => {
    const enField = `${fieldPrefix}En` as keyof AuditRecord;
    const arField = `${fieldPrefix}Ar` as keyof AuditRecord;

    const value = language === "ar" ? record[arField] : record[enField];
    return value ? String(value) : "";
  };

  const handleExportAll = async () => {
    if (!table) {
      return;
    }

    if (!startTime || !endTime) {
      toast.error(
        translate(t, "audit.errors.dateRangeRequired") ||
          "Please select a date range"
      );
      return;
    }

    setIsExporting(true);

    try {
      // Get visible columns preserving order
      const visibleColumns = table
        .getVisibleFlatColumns()
        .filter((col) => col.id !== "select" && col.id !== "actions");

      // Build query params to fetch ALL data
      const params = new URLSearchParams();
      params.append("start_time", startTime);
      params.append("end_time", endTime);
      params.append("skip", "0");
      params.append("limit", "999999"); // Fetch all records

      if (search) {
        params.append("search", search);
      }

      const url = `/analytics/audit?${params.toString()}`;

      // Fetch all data
      const response = await clientApi.get<{
        data: AuditRecord[];
        total: number;
      }>(url);

      if (!response.ok) {
        throw new Error(response.error || "Failed to fetch data");
      }

      if (!response.data) {
        throw new Error("No data received from server");
      }

      const allData = response.data.data || [];

      if (allData.length === 0) {
        toast.error(
          translate(t, "table.noDataToExport") || "No data to export"
        );
        return;
      }

      // Compose CSV header row
      const headerRow = visibleColumns
        .map((col) => getColumnHeader(col.id))
        .join(",");

      // Compose CSV data rows
      const dataRows = allData.map((record) =>
        visibleColumns
          .map((col) => {
            let value: unknown;

            // Handle bilingual fields
            if (col.id === "employeeName") {
              value = getBilingualValue(record, "employeeName");
            } else if (col.id === "department") {
              value = getBilingualValue(record, "department");
            } else if (col.id === "requester") {
              value = getBilingualValue(record, "requester");
            } else if (col.id === "mealType") {
              value = getBilingualValue(record, "mealType");
            } else {
              value = record[col.id as keyof AuditRecord];
            }

            return formatCellValue(value, col.id);
          })
          .join(",")
      );

      const csvContent = [headerRow, ...dataRows].join("\n");

      // Trigger CSV file download with UTF-8 BOM for Excel compatibility
      const BOM = "\uFEFF";
      const blob = new Blob([BOM + csvContent], {
        type: "text/csv;charset=utf-8",
      });
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;

      // Generate filename with date range and record count
      const startDate = new Date(startTime).toISOString().split("T")[0];
      const endDate = new Date(endTime).toISOString().split("T")[0];
      a.download = `${filename}_${startDate}_to_${endDate}_${allData.length}records.csv`;

      a.click();
      window.URL.revokeObjectURL(downloadUrl);

      // Show success toast
      const successMessage =
        translate(t, "table.exportSuccess") ||
        `Successfully exported ${allData.length} records`;
      toast.success(
        successMessage.replace("{count}", String(allData.length))
      );
    } catch (error) {
      console.error("Export failed:", error);
      toast.error(
        translate(t, "table.exportError") ||
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
      disabled={isExporting || !startTime || !endTime}
      icon={
        isExporting ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Download className="w-4 h-4" />
        )
      }
      tooltip={
        translate(t, "audit.exportAllTooltip") ||
        "Export all audit records to CSV"
      }
    >
      {isExporting
        ? translate(t, "table.exporting") || "Exporting..."
        : translate(t, "audit.exportAll") ||
          translate(t, "table.exportAll") ||
          "Export All"}
    </Button>
  );
}
