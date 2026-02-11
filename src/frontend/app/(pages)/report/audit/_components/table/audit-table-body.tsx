"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { DataTable } from "@/components/data-table";
import { Pagination } from "@/components/data-table/table/pagination";
import { AuditTableController } from "./audit-table-controller";
import { createAuditTableColumns } from "./audit-table-columns";
import type { AuditRecord } from "@/types/analytics.types";
import { clientApi } from "@/lib/http/axios-client";
import { useLanguage, translate } from "@/hooks/use-language";

interface AuditTableBodyProps {
  initialData: AuditRecord[];
  initialTotal: number;
  initialStartTime?: string;
  initialEndTime?: string;
}

/**
 * Response type for paginated audit data
 */
interface PaginatedAuditResponse {
  data: AuditRecord[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * Fetcher function for SWR - optimized for caching and deduping
 * Uses clientApi for authentication
 */
const fetcher = async (url: string): Promise<PaginatedAuditResponse> => {
  const response = await clientApi.get<PaginatedAuditResponse>(url);
  if (!response.ok) {
    throw new Error(response.error || "Failed to fetch");
  }
  return response.data;
};

export function AuditTableBody({
  initialData,
  initialTotal,
  initialStartTime,
  initialEndTime,
}: AuditTableBodyProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { t, language } = useLanguage();

  // Read URL parameters
  const page = Number(searchParams?.get("page") || "1");
  const limit = Number(searchParams?.get("limit") || "10");
  const search = searchParams?.get("search") || "";
  const startTimeParam =
    searchParams?.get("startTime") || initialStartTime || "";
  const endTimeParam = searchParams?.get("endTime") || initialEndTime || "";

  // State for date filters
  const [startTime, setStartTime] = useState(startTimeParam);
  const [endTime, setEndTime] = useState(endTimeParam);

  // Update URL with default dates on mount if missing
  useEffect(() => {
    // Only run on mount and if we have initial values but no URL params
    const hasUrlParams = searchParams?.has("startTime") && searchParams?.has("endTime");

    if (!hasUrlParams && initialStartTime && initialEndTime) {
      const params = new URLSearchParams(searchParams?.toString() || "");
      params.set("startTime", initialStartTime);
      params.set("endTime", initialEndTime);

      // Use replace to avoid adding to browser history
      router.replace(`/audit?${params.toString()}`, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  // State for total count (from server) - initialized with server-provided total
  const [totalCount, setTotalCount] = useState(initialTotal);

  // State for table instance
  const [tableInstance, setTableInstance] = useState<
    import("@tanstack/react-table").Table<AuditRecord> | null
  >(null);

  // Build API URL with current filters
  const params = new URLSearchParams();

  // Always include start_time and end_time first (required parameters)
  if (startTime) {
    params.append("start_time", startTime);
  }
  if (endTime) {
    params.append("end_time", endTime);
  }

  // Add pagination parameters
  params.append("skip", ((page - 1) * limit).toString());
  params.append("limit", limit.toString());

  // Add optional search filter
  if (search) {
    params.append("search", search);
  }

  // Construct the API URL - must include /audit path
  const apiUrl = `/analytics/audit?${params.toString()}`;

  // SWR hook with optimized configuration
  const { data, mutate, isLoading, error } = useSWR<PaginatedAuditResponse>(
    apiUrl,
    fetcher,
    {
      // Use server-side data as initial cache (wrapped in pagination structure)
      fallbackData: initialData
        ? { data: initialData, total: initialTotal, skip: 0, limit: 10 }
        : undefined,

      // Smooth transitions when changing filters/pagination
      keepPreviousData: true,

      // Refetch when component mounts
      revalidateOnMount: false,

      // Refetch if data is currently stale
      revalidateIfStale: true,

      // Disable automatic refetch on window focus (reduces API calls)
      revalidateOnFocus: false,

      // Disable automatic refetch on reconnect
      revalidateOnReconnect: false,

      // Update total count when data changes
      onSuccess: (paginatedData) => {
        if (paginatedData?.total !== undefined) {
          setTotalCount(paginatedData.total);
        }
      },
    }
  );

  // Memoize audit records to prevent dependency issues
  const auditRecords = useMemo(() => data?.data ?? [], [data]);

  // Update local state when URL params change
  useEffect(() => {
    const timer = setTimeout(() => {
      setStartTime(startTimeParam);
      setEndTime(endTimeParam);
    }, 0);

    return () => clearTimeout(timer);
  }, [startTimeParam, endTimeParam]);

  /**
   * Handle refresh
   */
  const handleRefresh = useCallback(() => {
    mutate();
  }, [mutate]);

  /**
   * Handle date filter changes
   */
  const handleStartTimeChange = useCallback((value: string) => {
    setStartTime(value);
  }, []);

  const handleEndTimeChange = useCallback((value: string) => {
    setEndTime(value);
  }, []);

  // Column translations
  const columnTranslations = useMemo(
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

  // Create columns
  const columns = useMemo(
    () => createAuditTableColumns({ language, t }),
    [language, t]
  );

  // Memoize sorted data
  const _data = useMemo(() => auditRecords, [auditRecords]);

  // Calculate pagination info using server-returned total count
  const totalItems = totalCount > 0 ? totalCount : auditRecords.length;
  const totalPages = Math.ceil(totalItems / limit);

  // Error state with retry button
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-red-500 mb-2">Failed to load audit records</div>
          <div className="text-gray-600 text-sm mb-4">{error.message}</div>
          <button
            onClick={() => mutate()}
            className="px-4 py-2 bg-blue-500 text-white hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-0 space-y-2">
      {/* Controller Bar - shrink-0 to maintain fixed height */}
      <div className="shrink-0">
        <AuditTableController
          onRefresh={handleRefresh}
          tableInstance={tableInstance}
          startTime={startTime}
          endTime={endTime}
          onStartTimeChange={handleStartTimeChange}
          onEndTimeChange={handleEndTimeChange}
          search={search}
          columnLabels={columnTranslations}
        />
      </div>

      {/* Table - flex-1 to fill remaining space, overflow handled by DataTable */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <DataTable
          columns={columns}
          _data={_data}
          tableInstanceHook={(table) => setTableInstance(table)}
          renderToolbar={() => null}
          enableRowSelection={false}
          enableSorting={false}
          _isLoading={isLoading}
        />
      </div>

      {/* Pagination - shrink-0 to maintain fixed height */}
      <div className="shrink-0 bg-card">
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          pageSize={limit}
          totalItems={totalItems}
        />
      </div>
    </div>
  );
}
