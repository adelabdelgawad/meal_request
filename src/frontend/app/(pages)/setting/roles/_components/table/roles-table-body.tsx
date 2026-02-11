"use client";

import {
  DataTable,
  TableHeader,
  TableController,
} from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/custom-toast";
import { ColumnDef } from "@tanstack/react-table";
import { Shield, FileText, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { AddRoleButton } from "../actions/add-role-button";
import { RoleActions } from "../actions/role-actions-menu";
import { StatusSwitch } from "@/components/ui/status-switch";
import { toggleRoleStatus } from "@/lib/api/roles";
import { RolesActionsProvider } from "@/app/(pages)/setting/roles/context/roles-actions-context";
import { useLanguage } from "@/hooks/use-language";
import type { RoleResponse } from "@/types/roles";

interface RolesTableBodyProps {
  roles: RoleResponse[];
  page: number;
  mutate: () => void;
  updateRoles: (updatedRoles: RoleResponse[]) => void;
}

export function RolesTableBody({
  roles,
  page,
  mutate,
  updateRoles,
}: RolesTableBodyProps) {
  const { t, language } = useLanguage();
  const settingRoles = (t as Record<string, unknown>).settingRoles as Record<string, unknown>;
  const columns_i18n = (settingRoles?.columns as Record<string, unknown>) || {};
  const toast_i18n = (settingRoles?.toast as Record<string, unknown>) || {};
  const confirmations_i18n = (settingRoles?.confirmations as Record<string, unknown>) || {};
  const itemName_i18n = (settingRoles?.itemName as Record<string, unknown>) || {};
  const searchPlaceholder = (settingRoles?.searchPlaceholder as string) || "Search roles...";
  const printTitle = (settingRoles?.printTitle as string) || "Role Management";

  // Helper function to get language-aware role name
  const getRoleName = (role: RoleResponse) =>
    language === "ar" ? (role.nameAr || role.nameEn) : role.nameEn;

  const [tableInstance, setTableInstance] = useState<import("@tanstack/react-table").Table<RoleResponse> | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<RoleResponse[]>([]);
  const [updatingIds, setUpdatingIds] = useState<Set<number>>(new Set());
  const isUpdating = updatingIds.size > 0;
  const selectedIds = selectedRoles
    .map((role) => role.id)
    .filter(Boolean) as number[];

  /**
   * Mark roles as being updated
   */
  const markUpdating = (ids: number[]) => {
    setUpdatingIds(new Set(ids));
  };

  /**
   * Clear updating state
   */
  const clearUpdating = () => {
    setUpdatingIds(new Set());
  };

  /**
   * Handle clear selection after bulk operations
   */
  const handleClearSelection = () => {
    setSelectedRoles([]);
  };

  const columns: ColumnDef<RoleResponse>[] = useMemo(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <div className="flex justify-center">
            <input
              type="checkbox"
              className="border-gray-300 cursor-pointer"
              checked={table.getIsAllPageRowsSelected()}
              onChange={(e) =>
                table.toggleAllPageRowsSelected(e.target.checked)
              }
              disabled={isUpdating}
            />
          </div>
        ),
        cell: ({ row }) => {
          const isRowUpdating =
            row.original.id && updatingIds.has(row.original.id);

          return (
            <div
              className={`flex justify-center items-center px-2 ${
                isRowUpdating ? "opacity-60" : ""
              }`}
            >
              {isRowUpdating && (
                <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
              )}
              {!isRowUpdating && (
                <input
                  type="checkbox"
                  className="border-gray-300 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  checked={row.getIsSelected()}
                  onChange={(e) => {
                    e.stopPropagation();
                    row.toggleSelected(e.target.checked);
                  }}
                  disabled={isUpdating || isRowUpdating ? true : undefined}
                />
              )}
            </div>
          );
        },
        enableSorting: false,
        enableHiding: false,
        size: 40,
      },
      {
        id: "nameEn",
        accessorKey: "nameEn",
        header: () => <div className="text-center">{(columns_i18n.nameEn as string) || "English Name"}</div>,
        cell: (info) => (
          <div className="flex items-center justify-center gap-2">
            <Shield className="w-4 h-4 text-gray-600 shrink-0" />
            <span className="font-medium">{info.getValue() as string}</span>
          </div>
        ),
        enableHiding: true,
      },
      {
        id: "nameAr",
        accessorKey: "nameAr",
        header: () => <div className="text-center">{(columns_i18n.nameAr as string) || "Arabic Name"}</div>,
        cell: (info) => (
          <div className="text-center">
            {(info.getValue() as string) || "—"}
          </div>
        ),
        enableHiding: true,
      },
      {
        id: "descriptionEn",
        accessorKey: "descriptionEn",
        header: () => <div className="text-center">{(columns_i18n.description as string) || "Description"}</div>,
        cell: (info) => (
          <div className="text-center text-sm text-gray-600">
            {(info.getValue() as string) || "—"}
          </div>
        ),
        enableHiding: true,
      },
      {
        id: "pages",
        accessorKey: "pagesNameEn",
        header: () => <div className="text-center">{(columns_i18n.pages as string) || "Pages"}</div>,
        cell: (info) => {
          const pages = info.getValue() as string[] | null;
          return (
            <div className="text-center">
              {pages && pages.length > 0 ? (
                <Badge variant="outline" className="text-xs">
                  <FileText className="me-1 h-3 w-3" />
                  {pages.length}
                </Badge>
              ) : (
                "—"
              )}
            </div>
          );
        },
        enableSorting: false,
        enableHiding: true,
      },
      {
        id: "totalUsers",
        accessorKey: "totalUsers",
        header: () => <div className="text-center">{(columns_i18n.users as string) || "Users"}</div>,
        cell: (info) => {
          const userCount = info.getValue() as number | null;
          return (
            <div className="text-center">
              {userCount !== null && userCount !== undefined ? (
                <Badge variant="outline" className="text-xs">
                  {userCount}
                </Badge>
              ) : (
                "—"
              )}
            </div>
          );
        },
        enableSorting: false,
        enableHiding: true,
      },
      {
        id: "isActive",
        accessorKey: "isActive",
        header: () => <div className="text-center">{(columns_i18n.active as string) || "Active"}</div>,
        cell: ({ row }) => {
          const role = row.original;
          const isUpdating = updatingIds.has(role.id);

          return (
            <div
              className={`flex justify-center ${
                isUpdating ? "opacity-60" : ""
              }`}
            >
              <StatusSwitch
                checked={role.isActive ?? false}
                onToggle={async () => {
                  await handleToggleStatus(role.id, !role.isActive);
                }}
                title={
                  role.isActive
                    ? (confirmations_i18n.deactivateTitle as string) || "Deactivate Role"
                    : (confirmations_i18n.activateTitle as string) || "Activate Role"
                }
                description={
                  role.isActive
                    ? ((confirmations_i18n.deactivateMessage as string) || 'Are you sure you want to deactivate "{roleName}"? Users with this role may lose access to certain features.').replace("{roleName}", getRoleName(role))
                    : ((confirmations_i18n.activateMessage as string) || 'Are you sure you want to activate "{roleName}"? Users with this role will regain their permissions.').replace("{roleName}", getRoleName(role))
                }
                size="sm"
              />
            </div>
          );
        },
        enableSorting: false,
        enableHiding: true,
      },
      {
        id: "actions",
        header: () => <div className="text-center">{(columns_i18n.actions as string) || "Actions"}</div>,
        cell: ({ row }) => (
          <div className="flex justify-center">
            <RoleActions role={row.original} />
          </div>
        ),
        enableSorting: false,
        enableHiding: false,
        size: 80,
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isUpdating, updatingIds, language]
  );

  // Handle disable roles
  const handleDisable = async (ids: number[]) => {
    try {
      if (ids.length === 0) {
        return;
      }

      // Filter to only active roles
      const activeRolesToDisable = roles.filter(
        (r) => r.id && ids.includes(r.id) && r.isActive
      );

      if (activeRolesToDisable.length === 0) {
        toast.info((toast_i18n.alreadyDisabled as string) || "Selected roles are already disabled");
        return;
      }

      const roleIdsToDisable = activeRolesToDisable.map((r) => r.id!);

      // Mark roles as updating
      markUpdating(roleIdsToDisable);

      // Call API for each role
      const updatedRoles: RoleResponse[] = [];
      for (const roleId of roleIdsToDisable) {
        const updated = await toggleRoleStatus(roleId, false);
        updatedRoles.push(updated);
      }

      // Update local state
      if (updatedRoles.length > 0) {
        updateRoles(updatedRoles);
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      const disabledMsg = ((toast_i18n.disabledMultiple as string) || "Successfully disabled {count} role(s)").replace("{count}", String(updatedRoles.length));
      toast.success(disabledMsg);

      // Keep selection for further actions
    } catch (error: unknown) {
      // Log technical error to console only
      console.error("Failed to disable roles:", error);
      // Show user-friendly error message
      toast.error((toast_i18n.disableError as string) || "Failed to disable roles");
    } finally {
      clearUpdating();
    }
  };

  // Handle enable roles
  const handleEnable = async (ids: number[]) => {
    try {
      if (ids.length === 0) {
        return;
      }

      // Filter to only inactive roles
      const inactiveRolesToEnable = roles.filter(
        (r) => r.id && ids.includes(r.id) && !r.isActive
      );

      if (inactiveRolesToEnable.length === 0) {
        toast.info((toast_i18n.alreadyEnabled as string) || "Selected roles are already enabled");
        return;
      }

      const roleIdsToEnable = inactiveRolesToEnable.map((r) => r.id!);

      // Mark roles as updating
      markUpdating(roleIdsToEnable);

      // Call API for each role
      const updatedRoles: RoleResponse[] = [];
      for (const roleId of roleIdsToEnable) {
        const updated = await toggleRoleStatus(roleId, true);
        updatedRoles.push(updated);
      }

      // Update local state
      if (updatedRoles.length > 0) {
        updateRoles(updatedRoles);
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      const enabledMsg = ((toast_i18n.enabledMultiple as string) || "Successfully enabled {count} role(s)").replace("{count}", String(updatedRoles.length));
      toast.success(enabledMsg);

      // Keep selection for further actions
    } catch (error: unknown) {
      // Log technical error to console only
      console.error("Failed to enable roles:", error);
      // Show user-friendly error message
      toast.error((toast_i18n.enableError as string) || "Failed to enable roles");
    } finally {
      clearUpdating();
    }
  };

  // Handle refresh
  const handleRefresh = () => {
    mutate();
  };

  // Handle toggle role status
  const handleToggleStatus = async (roleId: number, newStatus: boolean) => {
    try {
      markUpdating([roleId]);
      const updated = await toggleRoleStatus(roleId, newStatus);
      updateRoles([updated]);
      await new Promise((resolve) => setTimeout(resolve, 100));
      const successMsg = newStatus
        ? (toast_i18n.toggleEnabled as string) || "Role enabled successfully"
        : (toast_i18n.toggleDisabled as string) || "Role disabled successfully";
      toast.success(successMsg);
    } catch (error: unknown) {
      // Log technical error to console only
      console.error("Failed to toggle role status:", error);
      // Show user-friendly error message
      toast.error((toast_i18n.toggleError as string) || "Failed to toggle status");
      throw error;
    } finally {
      clearUpdating();
    }
  };

  // Handle update role
  const handleUpdateRole = (roleId: number, updatedRole: RoleResponse) => {
    updateRoles([updatedRole]);
  };

  // Update counts (placeholder - implement if needed)
  const updateCounts = async () => {
    // This would fetch fresh counts from the API
    // For now, just revalidate
    mutate();
  };

  // Create actions object for context provider
  const actions = {
    handleToggleStatus,
    handleUpdateRole,
    mutate,
    updateCounts,
    markUpdating,
    clearUpdating,
    updateRoles,
  };

  return (
    <RolesActionsProvider actions={actions}>
      <div className="h-full flex flex-col min-h-0 space-y-2">
        {/* Header Bar */}
        <TableHeader
          page={page}
          tableInstance={tableInstance}
          searchPlaceholder={searchPlaceholder}
          searchUrlParam="role_name"
          exportFilename="roles"
          printTitle={printTitle}
        />

        {/* Controller Bar */}
        <TableController
          selectedIds={selectedIds}
          isUpdating={isUpdating}
          onClearSelection={handleClearSelection}
          onDisable={(ids) => handleDisable(ids as number[])}
          onEnable={(ids) => handleEnable(ids as number[])}
          onRefresh={handleRefresh}
          tableInstance={tableInstance}
          itemName={(itemName_i18n.singular as string) || "role"}
          extraActions={<AddRoleButton />}
          columnLabels={{
            nameEn: (columns_i18n.nameEn as string) || "English Name",
            nameAr: (columns_i18n.nameAr as string) || "Arabic Name",
            descriptionEn: (columns_i18n.description as string) || "Description",
            pages: (columns_i18n.pages as string) || "Pages",
            totalUsers: (columns_i18n.users as string) || "Users",
            isActive: (columns_i18n.active as string) || "Active",
            actions: (columns_i18n.actions as string) || "Actions",
          }}
        />

        {/* Table */}
        <div className="flex-1 min-h-0 flex flex-col">
          <DataTable
            _data={roles}
            columns={columns}
            tableInstanceHook={(table) => setTableInstance(table)}
            onRowSelectionChange={setSelectedRoles}
            renderToolbar={() => null}
            enableRowSelection={true}
            enableSorting={false}
          />
        </div>
      </div>
    </RolesActionsProvider>
  );
}
