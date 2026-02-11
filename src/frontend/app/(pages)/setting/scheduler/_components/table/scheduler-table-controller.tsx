"use client";

import { TableController } from "@/components/data-table";
import { AddScheduleButton } from "../actions/add-schedule-button";
import type { ScheduledJob } from "@/types/scheduler";

interface SchedulerTableControllerProps {
  selectedIds: (number | string)[];
  isUpdating: boolean;
  onClearSelection: () => void;
  onDisable: (ids: (number | string)[]) => void;
  onEnable: (ids: (number | string)[]) => void;
  onRefresh: () => void;
  tableInstance: import("@tanstack/react-table").Table<ScheduledJob> | null;
  /** Translated labels for item name */
  itemName?: string;
  /** Map of column IDs to translated labels for column toggle menu */
  columnLabels?: Record<string, string>;
}

/**
 * Controller section of the scheduler table with bulk actions
 */
export function SchedulerTableController({
  selectedIds,
  isUpdating,
  onClearSelection,
  onDisable,
  onEnable,
  onRefresh,
  tableInstance,
  itemName = "job",
  columnLabels,
}: SchedulerTableControllerProps) {
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
      columnLabels={columnLabels}
      extraActions={<AddScheduleButton onAdd={onRefresh} />}
    />
  );
}
