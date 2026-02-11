"use client";

import { AuditTableBody } from "./table/audit-table-body";
import type { AuditRecord } from "@/types/analytics.types";

interface AuditTableProps {
  initialData: AuditRecord[];
  initialTotal: number;
  initialStartTime?: string;
  initialEndTime?: string;
}

export function AuditTable({
  initialData,
  initialTotal,
  initialStartTime,
  initialEndTime,
}: AuditTableProps) {
  return (
    <div className="flex flex-col gap-4 flex-1">
      <AuditTableBody
        initialData={initialData}
        initialTotal={initialTotal}
        initialStartTime={initialStartTime}
        initialEndTime={initialEndTime}
      />
    </div>
  );
}
