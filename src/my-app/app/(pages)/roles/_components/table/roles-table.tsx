"use client";

import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { Pagination } from "@/components/data-table";
import { StatusPanel } from "../sidebar/status-panel";
import { RolesTableBody } from "./roles-table-body";
import { RolesDataProvider } from "@/app/(pages)/roles/context/roles-data-context";
import LoadingSkeleton from "@/components/loading-skeleton";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { clientApi } from "@/lib/http/axios-client";
import type { SettingRolesResponse, RoleResponse } from "@/types/roles";
import type { PageResponse } from "@/types/pages";
import type { UserResponse } from "@/types/users";

interface RolesTableProps {
  initialData: SettingRolesResponse;
  preloadedPages: PageResponse[];
  preloadedUsers: UserResponse[];
}

/**
 * Fetcher function for SWR - optimized for caching and deduping
 * Uses clientApi for authentication
 */
const fetcher = async (url: string): Promise<SettingRolesResponse> => {
  const response = await clientApi.get<SettingRolesResponse>(url);
  if (!response.ok) {
    throw new Error(response.error || 'Failed to fetch');
  }
  return response.data;
};

function RolesTable({
  initialData,
  preloadedPages,
  preloadedUsers,
}: RolesTableProps) {
  const searchParams = useSearchParams();

  // Read URL parameters
  const page = Number(searchParams?.get("page") || "1");
  const limit = Number(searchParams?.get("limit") || "10");
  const _isActive = searchParams?.get("is_active") || "";
  const roleName = searchParams?.get("role_name") || "";
  const roleId = searchParams?.get("role_id") || "";

  // Build API URL with current filters - use Next.js API route
  const params = new URLSearchParams();
  params.append("skip", ((page - 1) * limit).toString());
  params.append("limit", limit.toString());
  if (_isActive) {
    params.append("is_active", _isActive);
  }
  if (roleName) {
    params.append("role_name", roleName);
  }
  if (roleId) {
    params.append("role_id", roleId);
  }

  const apiUrl = `/setting/roles?${params.toString()}`;

  // SWR hook with optimized configuration (from asset template)
  const { data, mutate, isLoading, error } = useSWR<SettingRolesResponse>(
    apiUrl,
    fetcher,
    {
      // Use server-side data as initial cache
      fallbackData: initialData ?? undefined,

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
    }
  );

  const roles = data?.roles ?? [];
  const activeCount = data?.activeCount ?? 0;
  const inactiveCount = data?.inactiveCount ?? 0;
  const totalItems = data?.total ?? 0;

  /**
   * Optimistic update helper - updates specific roles in SWR cache
   * Merges updated fields with existing role data to preserve extended fields
   * Also recalculates counts for StatusPanel
   */
  const updateRoles = async (updatedRoles: RoleResponse[]) => {
    // Use current data from component scope (works with fallbackData)
    // SWR's mutate callback only sees actual cache, not fallback data
    const currentData = data;

    if (!currentData) {
      return;
    }

    const updatedMap = new Map(updatedRoles.map((r) => [r.id, r]));

    // Merge updated roles with existing data to preserve extended fields
    // (totalUsers, pagesNameEn, pagesNameAr, etc.)
    const updatedRolesList = currentData.roles.map((role) => {
      if (updatedMap.has(role.id)) {
        return { ...role, ...updatedMap.get(role.id)! };
      }
      return role;
    });

    // Recalculate active/inactive counts based on updated roles
    const newActiveCount = updatedRolesList.filter((r) => r.isActive).length;
    const newInactiveCount = updatedRolesList.filter((r) => !r.isActive).length;

    const newData: SettingRolesResponse = {
      ...currentData,
      roles: updatedRolesList,
      activeCount: newActiveCount,
      inactiveCount: newInactiveCount,
    };

    // Pass the new data directly to mutate (not as an updater function)
    await mutate(newData, { revalidate: false });
  };

  // Error state with retry button (from template)
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-red-500 mb-2">Failed to load roles</div>
          <div className="text-gray-600 text-sm mb-4">{error.message}</div>
          <button onClick={() => mutate()}>Retry</button>
        </div>
      </div>
    );
  }

  const totalPages = Math.ceil(totalItems / limit);

  return (
    <RolesDataProvider pages={preloadedPages} users={preloadedUsers}>
      <div className="relative h-full flex gap-3 bg-muted/30 min-h-0 pt-1.5">
        {/* Loading Overlay */}
        {isLoading && <LoadingSkeleton />}

        {/* Status Panel */}
        <StatusPanel
          allRoles={activeCount + inactiveCount}
          activeRolesCount={activeCount}
          inactiveRolesCount={inactiveCount}
        />

        {/* Main Content - flex-1 to fill remaining width, flex-col for vertical stacking */}
        <ErrorBoundary>
          <div className="flex-1 flex flex-col min-h-0 min-w-0 space-y-2">
            {/* Table - flex-1 to take available vertical space */}
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <RolesTableBody
                roles={roles}
                page={page}
                mutate={mutate}
                updateRoles={updateRoles}
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
        </ErrorBoundary>
      </div>
    </RolesDataProvider>
  );
}

export default RolesTable;
