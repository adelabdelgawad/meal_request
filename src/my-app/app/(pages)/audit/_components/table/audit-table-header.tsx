"use client";

import { useMemo } from "react";
import { TableHeader, type ValueFormatter } from "@/components/data-table";
import { ExportAllButton } from "@/components/data-table/actions/export-all-button";
import type { AuditRecord } from "@/types/analytics.types";
import { useLanguage, translate } from "@/hooks/use-language";

interface AuditTableHeaderProps {
  page: number;
  pageSize?: number;
  tableInstance: import("@tanstack/react-table").Table<AuditRecord> | null;
  startTime?: string;
  endTime?: string;
  search?: string;
}

/**
 * Header section of the audit table with search and export controls
 */
export function AuditTableHeader({
  page,
  pageSize = 10,
  tableInstance,
  startTime,
  endTime,
  search,
}: AuditTableHeaderProps) {
  const { t, language } = useLanguage();

  // Value formatters for export (handles backend response format with language suffixes)
  const exportValueFormatters = useMemo<
    Record<string, ValueFormatter<AuditRecord>>
  >(
    () => ({
      // Format employeeName - pick language-specific field
      employeeName: (value, row) => {
        const name = language === "ar" ? row.employeeNameAr : row.employeeNameEn;
        return name || "-";
      },
      // Format department - pick language-specific field
      department: (value, row) => {
        const dept = language === "ar" ? row.departmentAr : row.departmentEn;
        return dept || "-";
      },
      // Format requester - select language-specific field
      requester: (value, row) => {
        const req = language === "ar" ? row.requesterAr : row.requesterEn;
        return req || "-";
      },
      // Format mealType - select language-specific field
      mealType: (value, row) => {
        const type = language === "ar" ? row.mealTypeAr : row.mealTypeEn;
        return type || "-";
      },
      // Format requestTime column
      requestTime: (value) => {
        return value ? formatDateTime(value as string, language) : "-";
      },
      // Format inTime column
      inTime: (value) => {
        return value ? formatDateTime(value as string, language) : "-";
      },
      // Format outTime column
      outTime: (value) => {
        return value ? formatDateTime(value as string, language) : "-";
      },
      // Format workingHours column
      workingHours: (value) => {
        return value !== null && value !== undefined ? value.toString() : "-";
      },
      // Format notes column
      notes: (value) => {
        return (value as string) || "-";
      },
    }),
    [language]
  );

  // Header labels for export (translated)
  const exportHeaderLabels = useMemo(
    () => ({
      code: translate(t, "audit.columns.code") || "Code",
      employeeName: translate(t, "audit.columns.name") || "Name",
      title: translate(t, "audit.columns.title") || "Title",
      department: translate(t, "audit.columns.department") || "Department",
      requester: translate(t, "audit.columns.requester") || "Requester",
      requesterTitle:
        translate(t, "audit.columns.requesterTitle") || "Requester Title",
      requestTime: translate(t, "audit.columns.requestTime") || "Request Time",
      mealType: translate(t, "audit.columns.mealType") || "Meal Type",
      inTime: translate(t, "audit.columns.attendanceIn") || "Attendance In",
      outTime: translate(t, "audit.columns.attendanceOut") || "Attendance Out",
      workingHours: translate(t, "audit.columns.hours") || "Hours",
      notes: translate(t, "audit.columns.notes") || "Notes",
    }),
    [t]
  );

  // Build filters for export
  const exportFilters = useMemo(
    () => ({
      start_time: startTime,
      end_time: endTime,
      search: search,
    }),
    [startTime, endTime, search]
  );

  return (
    <TableHeader
      page={page}
      tableInstance={tableInstance}
      searchPlaceholder={
        translate(t, "audit.searchPlaceholder") || "Search audit records..."
      }
      searchUrlParam="search"
      exportFilename={translate(t, "audit.exportFilename") || "audit_report"}
      printTitle={translate(t, "audit.printTitle") || "Audit Report"}
      showExport={false} // Disable default export button
      exportValueFormatters={exportValueFormatters}
      exportHeaderLabels={exportHeaderLabels}
      extraRight={
        <ExportAllButton<AuditRecord>
          table={tableInstance}
          apiEndpoint="/analytics/audit"
          filters={exportFilters}
          filename={translate(t, "audit.exportFilename") || "audit_report"}
          currentPage={page}
          pageSize={pageSize}
          valueFormatters={exportValueFormatters}
          headerLabels={exportHeaderLabels}
        />
      }
    />
  );
}

/**
 * Format date time for export
 */
function formatDateTime(dateString: string, language: string = "en"): string {
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return "-";
    }
    return date.toLocaleString(language === "ar" ? "ar-EG" : "en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return "-";
  }
}
