"use client";

import { ColumnDef } from "@tanstack/react-table";
import type { AuditRecord } from "@/types/analytics.types";
import { translate } from "@/hooks/use-language";

type Translations = {
  [key: string]: string | Translations;
};

interface AuditTableColumnsProps {
  language: string;
  t: Translations;
}

export function createAuditTableColumns({
  language,
  t,
}: AuditTableColumnsProps): ColumnDef<AuditRecord>[] {
  return [
    {
      accessorKey: "code",
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.code") || "Code"}
        </div>
      ),
      cell: ({ row }) => (
        <div className="text-center truncate" title={row.getValue("code")}>
          {row.getValue("code")}
        </div>
      ),
      size: 100,
      minSize: 100,
      maxSize: 150,
    },
    {
      id: "employeeName",
      accessorFn: (row) => language === "ar" ? row.employeeNameAr : row.employeeNameEn,
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.name") || "Name"}
        </div>
      ),
      cell: ({ row }) => {
        const localizedName = language === "ar" ? row.original.employeeNameAr : row.original.employeeNameEn;
        return (
          <div className="text-center truncate" title={localizedName}>
            {localizedName}
          </div>
        );
      },
      size: 150,
      minSize: 150,
      maxSize: 200,
    },
    {
      accessorKey: "title",
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.title") || "Title"}
        </div>
      ),
      cell: ({ row }) => (
        <div className="text-center truncate" title={row.getValue("title")}>
          {row.getValue("title")}
        </div>
      ),
      size: 150,
      minSize: 150,
      maxSize: 200,
    },
    {
      id: "department",
      accessorFn: (row) => language === "ar" ? row.departmentAr : row.departmentEn,
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.department") || "Department"}
        </div>
      ),
      cell: ({ row }) => {
        const localizedDept = language === "ar" ? row.original.departmentAr : row.original.departmentEn;
        return (
          <div className="text-center truncate" title={localizedDept}>
            {localizedDept}
          </div>
        );
      },
      size: 150,
      minSize: 150,
      maxSize: 200,
    },
    {
      id: "requester",
      accessorFn: (row) => language === "ar" ? row.requesterAr : row.requesterEn,
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.requester") || "Requester"}
        </div>
      ),
      cell: ({ row }) => {
        const localizedRequester = language === "ar" ? row.original.requesterAr : row.original.requesterEn;
        return (
          <div className="text-center truncate" title={localizedRequester}>
            {localizedRequester}
          </div>
        );
      },
      size: 150,
      minSize: 150,
      maxSize: 200,
    },
    {
      accessorKey: "requesterTitle",
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.requesterTitle") || "Requester Title"}
        </div>
      ),
      cell: ({ row }) => (
        <div
          className="text-center truncate"
          title={row.getValue("requesterTitle")}
        >
          {row.getValue("requesterTitle")}
        </div>
      ),
      size: 150,
      minSize: 150,
      maxSize: 200,
    },
    {
      accessorKey: "requestTime",
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.requestTime") || "Request Time"}
        </div>
      ),
      cell: ({ row }) => {
        const value = row.getValue("requestTime") as string | null;
        const formattedValue = value ? formatDateTime(value, language) : "-";
        return (
          <div className="text-center truncate" title={formattedValue}>
            {formattedValue}
          </div>
        );
      },
      size: 180,
      minSize: 180,
      maxSize: 200,
    },
    {
      id: "mealType",
      accessorFn: (row) => language === "ar" ? row.mealTypeAr : row.mealTypeEn,
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.mealType") || "Meal Type"}
        </div>
      ),
      cell: ({ row }) => {
        const localizedMealType = language === "ar" ? row.original.mealTypeAr : row.original.mealTypeEn;
        return (
          <div className="text-center truncate" title={localizedMealType}>
            {localizedMealType}
          </div>
        );
      },
      size: 120,
      minSize: 120,
      maxSize: 150,
    },
    {
      accessorKey: "inTime",
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.attendanceIn") || "Attendance In"}
        </div>
      ),
      cell: ({ row }) => {
        const value = row.getValue("inTime") as string | null;
        const formattedValue = value ? formatDateTime(value, language) : "-";
        return (
          <div className="text-center truncate" title={formattedValue}>
            {formattedValue}
          </div>
        );
      },
      size: 180,
      minSize: 180,
      maxSize: 200,
    },
    {
      accessorKey: "outTime",
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.attendanceOut") || "Attendance Out"}
        </div>
      ),
      cell: ({ row }) => {
        const value = row.getValue("outTime") as string | null;
        const formattedValue = value ? formatDateTime(value, language) : "-";
        return (
          <div className="text-center truncate" title={formattedValue}>
            {formattedValue}
          </div>
        );
      },
      size: 180,
      minSize: 180,
      maxSize: 200,
    },
    {
      accessorKey: "workingHours",
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.hours") || "Hours"}
        </div>
      ),
      cell: ({ row }) => {
        const value = row.getValue("workingHours") as number | null;
        const displayValue = value !== null ? value.toString() : "-";
        return (
          <div className="text-center truncate" title={displayValue}>
            {displayValue}
          </div>
        );
      },
      size: 80,
      minSize: 80,
      maxSize: 100,
    },
    {
      accessorKey: "notes",
      header: () => (
        <div className="text-center font-semibold">
          {translate(t, "audit.columns.notes") || "Notes"}
        </div>
      ),
      cell: ({ row }) => {
        const value = row.getValue("notes") as string | null;
        const displayValue = value || "-";
        return (
          <div className="text-center truncate" title={displayValue}>
            {displayValue}
          </div>
        );
      },
      size: 200,
      minSize: 200,
      maxSize: 300,
    },
  ];
}

/**
 * Format date time for display in table cells
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
