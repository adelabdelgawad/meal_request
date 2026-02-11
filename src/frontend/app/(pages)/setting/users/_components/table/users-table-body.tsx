"use client";

import { DataTable } from "@/components/data-table";
import { useMemo, useState, useCallback } from "react";
import type {
  UserWithRolesResponse,
  SimpleRole,
} from "@/types/users";
import { UsersTableHeader } from "./users-table-header";
import { UsersTableController } from "./users-table-controller";
import { createUsersTableColumns } from "./users-table-columns";
import { useUsersTableActions } from "./users-table-actions";
import { UserActions } from "../actions/actions-menu";
import { useLanguage, translate } from "@/hooks/use-language";

interface UsersTableBodyProps {
  users: UserWithRolesResponse[];
  page: number;
  mutate: () => void;
  updateUsers: (updatedUsers: UserWithRolesResponse[]) => Promise<void>;
  roleOptions: SimpleRole[];
}

export default function UsersTableBody({
  users,
  page,
  mutate,
  updateUsers,
  roleOptions,
}: UsersTableBodyProps) {
  const { t, language } = useLanguage();
  const [tableInstance, setTableInstance] = useState<
    import("@tanstack/react-table").Table<UserWithRolesResponse> | null
  >(null);
  const [selectedUsers, setSelectedUsers] = useState<UserWithRolesResponse[]>(
    []
  );
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());
  const isUpdating = updatingIds.size > 0;

  // Column translations
  const columnTranslations = useMemo(() => ({
    username: translate(t, 'users.columns.username'),
    fullName: translate(t, 'users.columns.fullName'),
    email: translate(t, 'users.columns.email'),
    title: translate(t, 'users.columns.title'),
    source: translate(t, 'users.columns.source') || 'Source',
    override: translate(t, 'users.columns.override') || 'Override',
    active: translate(t, 'users.columns.active'),
    blocked: translate(t, 'users.columns.blocked'),
    roles: translate(t, 'users.columns.roles'),
    departments: translate(t, 'users.columns.departments') || 'Departments',
    allDepartments: translate(t, 'users.departments.allDepartments') || 'ALL',
    actions: translate(t, 'users.columns.actions'),
    noRoles: translate(t, 'table.noRoles'),
    activateUser: translate(t, 'users.confirmations.activateTitle'),
    deactivateUser: translate(t, 'users.confirmations.deactivateTitle'),
    activateMessage: translate(t, 'users.confirmations.activateMessage'),
    deactivateMessage: translate(t, 'users.confirmations.deactivateMessage'),
    activateSuccess: translate(t, 'users.toast.activateSuccess'),
    deactivateSuccess: translate(t, 'users.toast.deactivateSuccess'),
    blockUser: translate(t, 'users.block.blockUser'),
    unblockUser: translate(t, 'users.block.unblockUser'),
    blockMessage: translate(t, 'users.block.blockMessage'),
    unblockMessage: translate(t, 'users.block.unblockMessage'),
    blockSuccess: translate(t, 'users.block.blockSuccess'),
    unblockSuccess: translate(t, 'users.block.unblockSuccess'),
  }), [t]);

  const selectedIds = selectedUsers
    .map((user) => user.id)
    .filter(Boolean) as string[];

  /**
   * Mark users as being updated
   */
  const markUpdating = useCallback((ids: string[]) => {
    setUpdatingIds(new Set(ids));
  }, []);

  /**
   * Clear updating state
   */
  const clearUpdating = useCallback(
    (ids?: string[]) => {
      if (ids && ids.length > 0) {
        const newSet = new Set(updatingIds);
        ids.forEach((_id) => newSet.delete(_id));
        setUpdatingIds(newSet);
      } else {
        setUpdatingIds(new Set());
      }
    },
    [updatingIds]
  );

  /**
   * Handle clear selection after bulk operations
   */
  const handleClearSelection = useCallback(() => {
    setSelectedUsers([]);
    // Also clear the table instance's internal row selection state
    if (tableInstance) {
      tableInstance.resetRowSelection();
    }
  }, [tableInstance]);

  /**
   * Handle refresh
   */
  const handleRefresh = useCallback(() => {
    mutate();
  }, [mutate]);

  // Toast messages for bulk actions
  const toastMessages = useMemo(() => ({
    enabledMultiple: translate(t, 'users.toast.enabledMultiple'),
    disabledMultiple: translate(t, 'users.toast.disabledMultiple'),
    alreadyEnabled: translate(t, 'users.toast.alreadyEnabled'),
    alreadyDisabled: translate(t, 'users.toast.alreadyDisabled'),
    enableError: translate(t, 'users.toast.enableError'),
    disableError: translate(t, 'users.toast.disableError'),
  }), [t]);

  // Get bulk action handlers
  const { handleDisable, handleEnable } = useUsersTableActions({
    users,
    updateUsers,
    markUpdating,
    clearUpdating,
    toastMessages,
  });

  // Create columns with actions
  const columns = useMemo(
    () =>
      createUsersTableColumns({
        updatingIds,
        mutate,
        updateUsers,
        markUpdating,
        clearUpdating,
        translations: columnTranslations,
        roleOptions,
        language,
      }).map((column) => {
        // Special handling for actions column to include UserActions
        if (column.id === "actions") {
          return {
            ...column,
            cell: ({ row }: { row: { original: UserWithRolesResponse } }) => {
              const isRowUpdating = Boolean(
                row.original.id && updatingIds.has(row.original.id)
              );
              return (
                <div
                  className={`flex justify-center pe-4 ${
                    isRowUpdating ? "opacity-60 pointer-events-none" : ""
                  }`}
                  onClick={(e) => e.stopPropagation()}
                >
                  <UserActions
                    user={row.original}
                    onUpdate={mutate}
                    onUserUpdated={async (updatedUser) => {
                      // Update the specific user in the table
                      await updateUsers([updatedUser]);
                      // Refetch to get accurate role counts from backend
                      mutate();
                    }}
                    disabled={isRowUpdating}
                  />
                </div>
              );
            },
          };
        }
        return column;
      }),
    [updatingIds, updateUsers, mutate, markUpdating, clearUpdating, columnTranslations, roleOptions, language]
  );

  // Memoize sorted _data
  const _data = useMemo(() => users, [users]);

  return (
    <div className="h-full flex flex-col min-h-0 space-y-2">
      {/* Header Bar - shrink-0 to maintain fixed height */}
      <div className="shrink-0">
        <UsersTableHeader page={page} tableInstance={tableInstance} roleOptions={roleOptions} />
      </div>

      {/* Controller Bar - shrink-0 to maintain fixed height */}
      <div className="shrink-0">
        <UsersTableController
          selectedIds={selectedIds}
          isUpdating={isUpdating}
          onClearSelection={handleClearSelection}
          onDisable={handleDisable}
          onEnable={handleEnable}
          onRefresh={handleRefresh}
          tableInstance={tableInstance}
          itemName={translate(t, 'users.itemName.singular') || "user"}
          columnLabels={{
            username: columnTranslations.username,
            fullName: columnTranslations.fullName,
            email: columnTranslations.email,
            title: columnTranslations.title,
            isActive: columnTranslations.active,
            roles: columnTranslations.roles,
            departments: columnTranslations.departments,
            actions: columnTranslations.actions,
          }}
        />
      </div>

      {/* Table - flex-1 to fill remaining space, overflow handled by DataTable */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <DataTable
          columns={columns}
          _data={_data}
          tableInstanceHook={(table) => setTableInstance(table)}
          onRowSelectionChange={setSelectedUsers}
          renderToolbar={() => null}
          enableRowSelection={true}
          enableSorting={false}
        />
      </div>
    </div>
  );
}
