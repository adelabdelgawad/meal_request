import { AuditTable } from "./_components/audit-table";
import { getAuditReport } from "@/lib/actions/audit.actions";
import type { AuditFilters } from "@/types/analytics.types";

interface AuditPageProps {
  searchParams: Promise<{ startTime?: string; endTime?: string }>;
}

export default async function AuditPage({ searchParams }: AuditPageProps) {
  const params = await searchParams;

  // Provide default time range if none provided (default to today)
  const now = new Date();
  const defaultStartTime =
    params.startTime ||
    new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
      0,
      0,
      0,
      0
    ).toISOString();
  const defaultEndTime =
    params.endTime ||
    new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
      23,
      59,
      59,
      999
    ).toISOString();

  // Create filters for server action
  const filters: AuditFilters = {
    startTime: defaultStartTime,
    endTime: defaultEndTime,
  };

  // Fetch audit data on the server using server action
  const paginatedResponse = await getAuditReport(filters);

  return (
    <div className="flex flex-col h-full p-4 md:p-6">
      <AuditTable
        initialData={paginatedResponse.data}
        initialTotal={paginatedResponse.total}
        initialStartTime={defaultStartTime}
        initialEndTime={defaultEndTime}
      />
    </div>
  );
}
