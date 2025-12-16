"use client";

import React from "react";
import { Table } from "@tanstack/react-table";
import { DynamicTableBar } from "./data-table-bar";
import { SelectionDisplay } from "../actions/selection-display";
import { EnableButton } from "../actions/enable-button";
import { DisableButton } from "../actions/disable-button";
import { RefreshButton } from "../controls/refresh-button";
import { ColumnToggleButton } from "../controls/column-toggle-button";

export interface TableControllerProps<TData> {
  /** Array of selected item IDs */
  selectedIds: (string | number)[];
  /** Whether any items are currently being updated */
  isUpdating: boolean;
  /** Callback to clear selection */
  onClearSelection: () => void;
  /** Callback when disable is triggered */
  onDisable: (ids: (string | number)[]) => void;
  /** Callback when enable is triggered */
  onEnable: (ids: (string | number)[]) => void;
  /** Callback to refresh the table data */
  onRefresh: () => void;
  /** Table instance for column toggle */
  tableInstance: Table<TData> | null;
  /** Label for items (default: "item") */
  itemName?: string;
  /** Whether to show disable button (default: true) */
  showDisable?: boolean;
  /** Whether to show enable button (default: true) */
  showEnable?: boolean;
  /** Whether to show refresh button (default: true) */
  showRefresh?: boolean;
  /** Whether to show column toggle button (default: true) */
  showColumnToggle?: boolean;
  /** Additional content to render before the action buttons */
  extraActions?: React.ReactNode;
  /** Additional content to render after the action buttons */
  extraActionsEnd?: React.ReactNode;
  /** Map of column IDs to translated labels for column toggle menu */
  columnLabels?: Record<string, string>;
}

/**
 * Reusable table controller component with selection display and bulk actions.
 * Wraps DynamicTableBar with common table control functionality.
 */
export function TableController<TData>({
  selectedIds,
  isUpdating,
  onClearSelection,
  onDisable,
  onEnable,
  onRefresh,
  tableInstance,
  itemName = "item",
  showDisable = true,
  showEnable = true,
  showRefresh = true,
  showColumnToggle = true,
  extraActions,
  extraActionsEnd,
  columnLabels,
}: TableControllerProps<TData>) {
  return (
    <div className="shrink-0">
      <DynamicTableBar
        variant="controller"
        hasSelection={selectedIds.length > 0}
        left={
          <SelectionDisplay
            selectedCount={selectedIds.length}
            onClearSelection={onClearSelection}
            itemName={itemName}
          />
        }
        right={
          <>
            {extraActions}
            {showDisable && (
              <DisableButton
                selectedIds={selectedIds}
                onDisable={onDisable}
                disabled={isUpdating}
              />
            )}
            {showEnable && (
              <EnableButton
                selectedIds={selectedIds}
                onEnable={onEnable}
                disabled={isUpdating}
              />
            )}
            {showRefresh && <RefreshButton onRefresh={onRefresh} />}
            {showColumnToggle && <ColumnToggleButton table={tableInstance} columnLabels={columnLabels} />}
            {extraActionsEnd}
          </>
        }
      />
    </div>
  );
}
