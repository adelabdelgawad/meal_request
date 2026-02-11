"use client";

import { useState } from "react";
import { Printer, Loader2 } from "lucide-react";
import { Table } from "@tanstack/react-table";
import { Button } from "@/components/data-table";
import { useLanguage, translate } from "@/hooks/use-language";
import { clientApi } from "@/lib/http/axios-client";
import { toast } from "@/components/ui/custom-toast";
import type { AuditRecord } from "@/types/analytics.types";

interface PrintAllAuditButtonProps {
  /** Table instance to get visible columns */
  table: Table<AuditRecord> | null;
  /** Start time filter */
  startTime: string;
  /** End time filter */
  endTime: string;
  /** Search filter */
  search?: string;
  /** Title for print document */
  title?: string;
}

export function PrintAllAuditButton({
  table,
  startTime,
  endTime,
  search,
  title = "Audit Report",
}: PrintAllAuditButtonProps) {
  const { t, language } = useLanguage();
  const [isPrinting, setIsPrinting] = useState(false);

  /**
   * Format a cell value for display
   */
  const formatCellValue = (value: unknown): string => {
    if (value === undefined || value === null) {
      return "";
    }

    if (typeof value === "boolean") {
      return value ? translate(t, "common.yes") : translate(t, "common.no");
    }

    if (value instanceof Date) {
      return value.toLocaleString(language === "ar" ? "ar-SA" : "en-US");
    }

    return String(value);
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

  const handlePrintAll = async () => {
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

    setIsPrinting(true);

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
          translate(t, "table.noDataToPrint") || "No data to print"
        );
        return;
      }

      // Compose HTML header row
      const headersHtml = visibleColumns
        .map((col) => `<th>${getColumnHeader(col.id)}</th>`)
        .join("");

      // Compose HTML data rows
      const rowsHtml = allData
        .map((record) => {
          const cells = visibleColumns
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

              return `<td>${formatCellValue(value)}</td>`;
            })
            .join("");

          return `<tr>${cells}</tr>`;
        })
        .join("");

      // Format date range for display
      const startDate = new Date(startTime).toLocaleDateString(
        language === "ar" ? "ar-SA" : "en-US"
      );
      const endDate = new Date(endTime).toLocaleDateString(
        language === "ar" ? "ar-SA" : "en-US"
      );

      const printContent = `
        <html>
          <head>
            <title>${title}</title>
            <style>
              body {
                font-family: Arial, sans-serif;
                padding: 20px;
                direction: ${language === "ar" ? "rtl" : "ltr"};
              }
              h1 {
                font-size: 24px;
                margin-bottom: 10px;
                text-align: center;
              }
              .date-range {
                font-size: 14px;
                color: #666;
                text-align: center;
                margin-bottom: 20px;
              }
              .record-count {
                font-size: 12px;
                color: #666;
                text-align: center;
                margin-bottom: 20px;
              }
              table {
                width: 100%;
                border-collapse: collapse;
                border: 1px solid #000;
                font-size: 12px;
              }
              th, td {
                border: 1px solid #000;
                padding: 6px;
                text-align: ${language === "ar" ? "right" : "left"};
              }
              th {
                background-color: #f3f4f6;
                font-weight: bold;
              }
              tr:nth-child(even) {
                background-color: #f9fafb;
              }
              @media print {
                body { padding: 10px; }
                h1 { font-size: 20px; }
                table { font-size: 10px; }
                th, td { padding: 4px; }
              }
            </style>
          </head>
          <body>
            <h1>${title}</h1>
            <div class="date-range">
              ${translate(t, "audit.dateRange") || "Date Range"}: ${startDate} - ${endDate}
            </div>
            <div class="record-count">
              ${translate(t, "audit.totalRecords") || "Total Records"}: ${allData.length}
            </div>
            <table>
              <thead>
                <tr>${headersHtml}</tr>
              </thead>
              <tbody>
                ${rowsHtml}
              </tbody>
            </table>
          </body>
        </html>
      `;

      const printWindow = window.open("", "", "width=1200,height=800");
      if (printWindow) {
        printWindow.document.write(printContent);
        printWindow.document.close();
        printWindow.focus();

        // Wait for content to load before printing
        printWindow.onload = () => {
          printWindow.print();
        };
      } else {
        toast.error(
          translate(t, "audit.errors.popupBlocked") ||
            "Please allow popups to print"
        );
      }
    } catch (error) {
      console.error("Print failed:", error);
      toast.error(
        translate(t, "table.printError") ||
          "Failed to print data. Please try again."
      );
    } finally {
      setIsPrinting(false);
    }
  };

  return (
    <Button
      variant="default"
      size="default"
      onClick={handlePrintAll}
      disabled={isPrinting || !startTime || !endTime}
      icon={
        isPrinting ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Printer className="w-4 h-4" />
        )
      }
      tooltip={
        translate(t, "audit.printAllTooltip") ||
        "Print all audit records"
      }
    >
      {isPrinting
        ? translate(t, "table.printing") || "Printing..."
        : translate(t, "audit.printAll") ||
          translate(t, "table.print") ||
          "Print All"}
    </Button>
  );
}
