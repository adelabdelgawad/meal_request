"use client";

import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import type {
  SettingUsersResponse,
  UserWithRolesResponse,
  RoleResponse,
} from "@/types/users";
import type { DepartmentForAssignment } from "@/lib/actions/departments.actions";
import { StatusPanel } from "../sidebar/status-panel";
import UsersTableBody from "./users-table-body";
import LoadingSkeleton from "@/components/loading-skeleton";
import { clientApi } from "@/lib/http/axios-client";
import { UsersProvider } from "../../context/users-actions-context";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Pagination } from "@/components/data-table/table/pagination";

interface UsersTableProps {
  initialData: SettingUsersResponse | null;
  roles: RoleResponse[];
  domainUsers?: unknown[];
  departments: DepartmentForAssignment[];
}

/**
 * Fetcher function for SWR - optimized for caching and deduping
 * Uses clientApi for authentication
 */
const fetcher = async (url: string): Promise<SettingUsersResponse> => {
  const response = await clientApi.get<SettingUsersResponse>(url);
  if (!response.ok) {
    throw new Error(response.error || "Failed to fetch");
  }
  return response.data;
};

function UsersTable({ initialData, roles, departments }: UsersTableProps) {
  const searchParams = useSearchParams();

  // Read URL parameters
  const page = Number(searchParams?.get("page") || "1");
  const limit = Number(searchParams?.get("limit") || "10");
  const filter = searchParams?.get("filter") || "";
  const _isActive = searchParams?.get("is_active") || "";
  const role = searchParams?.get("role") || "";

  // Build API URL with current filters - use Next.js API route
  const params = new URLSearchParams();
  params.append("skip", ((page - 1) * limit).toString());
  params.append("limit", limit.toString());
  if (filter) {
    params.append("username", filter);
  }
  if (_isActive) {
    params.append("is_active", _isActive);
  }
  if (role) {
    params.append("role", role);
  }

  const apiUrl = `/setting/users?${params.toString()}`;

  // SWR hook with optimized configuration (from asset template)
  const { data, mutate, isLoading, error } = useSWR<SettingUsersResponse>(
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

  const users = data?.users ?? [];
  const activeCount = data?.activeCount ?? 0;
  const inactiveCount = data?.inactiveCount ?? 0;

  /**
   * Update helper - updates specific users in SWR cache with server response
   * Also recalculates counts for StatusPanel including role counts
   */
  const updateUsers = async (updatedUsers: UserWithRolesResponse[]) => {
    await mutate(
      (currentData: SettingUsersResponse | undefined) => {
        if (!currentData) {
          return currentData;
        }

        const updatedMap = new Map(
          updatedUsers.map((u: UserWithRolesResponse) => [u.id, u])
        );

        // Update users with new data
        const updatedUsersList = currentData.users.map(
          (user: UserWithRolesResponse) =>
            updatedMap.has(user.id) ? updatedMap.get(user.id)! : user
        );

        // Recalculate counts based on updated users
        const newActiveCount = updatedUsersList.filter(
          (user: UserWithRolesResponse) => user.isActive
        ).length;
        const newInactiveCount = updatedUsersList.filter(
          (user: UserWithRolesResponse) => !user.isActive
        ).length;

        // Recalculate role counts from all users' roleIds
        const roleCounts: Record<number, number> = {};
        updatedUsersList.forEach((user: UserWithRolesResponse) => {
          if (user.roleIds && Array.isArray(user.roleIds)) {
            user.roleIds.forEach((roleId: number) => {
              roleCounts[roleId] = (roleCounts[roleId] || 0) + 1;
            });
          }
        });

        // Update roleOptions with new counts
        const updatedRoleOptions = currentData.roleOptions.map((role) => ({
          ...role,
          totalUsers: roleCounts[role.id] || 0,
        }));

        return {
          ...currentData,
          users: updatedUsersList,
          activeCount: newActiveCount,
          inactiveCount: newInactiveCount,
          roleOptions: updatedRoleOptions,
        };
      },
      { revalidate: false } // Prevents automatic refetch
    );
  };

  // Error state with retry button (from template)
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-red-500 mb-2">Failed to load users</div>
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

  const totalItems = data?.total ?? 0;
  const totalPages = Math.ceil(totalItems / limit);

  // Define actions for the context provider
  const actions = {
    onToggleUserStatus: async (userId: string, isActive: boolean) => {
      try {
        // Call API and wait for server response
        const response = await clientApi.put<UserWithRolesResponse>(
          `/setting/users/${userId}/status`,
          {
            userId, // camelCase in request body
            isActive, // camelCase in request body
          }
        );
        if (!response.ok) {
          return {
            success: false,
            error: response.error || "Failed to update status",
          };
        }
        const result = response.data;
        // Update UI only with server response
        if (result) {
          await updateUsers([result]);
        }
        return {
          success: true,
          message: `User ${isActive ? "enabled" : "disabled"} successfully`,
        };
      } catch (error: unknown) {
        const apiError = error as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          apiError.response?.data?.detail ||
          apiError.message ||
          "Failed to update status";
        return {
          success: false,
          error: errorMessage,
        };
      }
    },
    onUpdateUser: async (
      userId: string,
      updatedUser: {
        fullname?: string | null;
        title?: string | null;
        roleIds: number[];
      }
    ) => {
      try {
        const response = await clientApi.put<UserWithRolesResponse>(
          `/setting/users/${userId}`,
          updatedUser
        );
        if (!response.ok) {
          return {
            success: false,
            error: response.error || "Failed to update user",
          };
        }
        const result = response.data;
        // Update UI with server response
        if (result) {
          await updateUsers([result]);
        }
        return {
          success: true,
          message: "User updated successfully",
          data: result,
        };
      } catch (error: unknown) {
        const apiError = error as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          apiError.response?.data?.detail ||
          apiError.message ||
          "Failed to update user";
        return {
          success: false,
          error: errorMessage,
        };
      }
    },
    updateUsers,
    onBulkUpdateStatus: async (userIds: string[], isActive: boolean) => {
      try {
        const response = await clientApi.put<{
          updatedUsers: UserWithRolesResponse[];
        }>(`/setting/users/status`, {
          userIds, // camelCase in request body
          isActive, // camelCase in request body
        });
        if (!response.ok) {
          return {
            success: false,
            error: response.error || "Failed to update status",
          };
        }
        const result = response.data;
        // Update UI with server response
        if (result?.updatedUsers && result.updatedUsers.length > 0) {
          await updateUsers(result.updatedUsers);
        }
        return {
          success: true,
          message: `Successfully ${isActive ? "enabled" : "disabled"} ${
            userIds.length
          } user(s)`,
          data: result?.updatedUsers,
        };
      } catch (error: unknown) {
        const apiError = error as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          apiError.response?.data?.detail ||
          apiError.message ||
          "Failed to update users status";
        return {
          success: false,
          error: errorMessage,
        };
      }
    },
    onRefreshUsers: async () => {
      await mutate();
      return {
        success: true,
        message: "Users refreshed",
        data: null,
      };
    },
  };

  return (
    <UsersProvider actions={actions} roles={roles} departments={departments}>
      <div className="relative h-full flex gap-3 bg-muted/30 min-h-0 pt-1.5">
        {/* Loading Overlay */}
        {isLoading && <LoadingSkeleton />}

        {/* Status Panel */}
        <StatusPanel
          allUsers={activeCount + inactiveCount}
          activeUsersCount={activeCount}
          inactiveUsersCount={inactiveCount}
          roleOptions={data?.roleOptions ?? []}
        />

        {/* Main Content - flex-1 to fill remaining width, flex-col for vertical stacking */}
        <ErrorBoundary>
          <div className="flex-1 flex flex-col min-h-0 min-w-0 space-y-2">
            {/* Table - flex-1 to take available vertical space */}
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <UsersTableBody
                users={users}
                page={page}
                mutate={mutate}
                updateUsers={updateUsers}
                roleOptions={data?.roleOptions ?? []}
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
    </UsersProvider>
  );
}

export default UsersTable;
