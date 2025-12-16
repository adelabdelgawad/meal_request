"use client";

import { TableController } from "@/components/data-table";
import { AddUserButton } from "../actions/add-user-button";
import type { UserWithRolesResponse } from "@/types/users";

interface UsersTableControllerProps {
  selectedIds: string[];
  isUpdating: boolean;
  onClearSelection: () => void;
  onDisable: (ids: string[]) => void;
  onEnable: (ids: string[]) => void;
  onRefresh: () => void;
  tableInstance: import("@tanstack/react-table").Table<UserWithRolesResponse> | null;
  /** Translated labels for item name */
  itemName?: string;
  /** Map of column IDs to translated labels for column toggle menu */
  columnLabels?: Record<string, string>;
}

/**
 * Controller section of the users table with bulk actions
 */
export function UsersTableController({
  selectedIds,
  isUpdating,
  onClearSelection,
  onDisable,
  onEnable,
  onRefresh,
  tableInstance,
  itemName = "user",
  columnLabels,
}: UsersTableControllerProps) {
  return (
    <TableController
      selectedIds={selectedIds}
      isUpdating={isUpdating}
      onClearSelection={onClearSelection}
      onDisable={(ids) => onDisable(ids as string[])}
      onEnable={(ids) => onEnable(ids as string[])}
      onRefresh={onRefresh}
      tableInstance={tableInstance}
      itemName={itemName}
      extraActions={<AddUserButton onAdd={onRefresh} />}
      columnLabels={columnLabels}
    />
  );
}
