"use client";

import { DataTable } from "@/components/data-table";
import { useMemo, useState, useCallback } from "react";
import type { ScheduledJob } from "@/types/scheduler";
import { SchedulerTableHeader } from "./scheduler-table-header";
import { SchedulerTableController } from "./scheduler-table-controller";
import { createSchedulerTableColumns } from "./scheduler-table-columns";
import { useSchedulerTableActions } from "./scheduler-table-actions";
import { JobActions } from "../actions/actions-menu";
import { useLanguage, translate } from "@/hooks/use-language";
import { useSchedulerActions } from "../../context/scheduler-actions-context";
import { toast } from "sonner";

interface SchedulerTableBodyProps {
  jobs: ScheduledJob[];
  page: number;
}

export default function SchedulerTableBody({
  jobs,
  page,
}: SchedulerTableBodyProps) {
  const { t, language } = useLanguage();
  // Get actions from context (no longer from props)
  const { onToggleJobEnabled, updateJobs, onRefreshJobs } =
    useSchedulerActions();
  const [tableInstance, setTableInstance] = useState<
    import("@tanstack/react-table").Table<ScheduledJob> | null
  >(null);
  const [selectedJobs, setSelectedJobs] = useState<ScheduledJob[]>([]);
  const [updatingIds, setUpdatingIds] = useState<Set<number | string>>(
    new Set()
  );
  const isUpdating = updatingIds.size > 0;

  // Column translations
  const columnTranslations = useMemo(
    () => ({
      jobKey: translate(t, "scheduler.columns.jobKey") || "Job Key",
      name: translate(t, "scheduler.columns.name") || "Name",
      type: translate(t, "scheduler.columns.type") || "Type",
      schedule: translate(t, "scheduler.columns.schedule") || "Schedule",
      priority: translate(t, "scheduler.columns.priority") || "Priority",
      enabled: translate(t, "scheduler.columns.enabled") || "Enabled",
      nextRun: translate(t, "scheduler.columns.nextRun") || "Next Run",
      lastRun: translate(t, "scheduler.columns.lastRun") || "Last Run",
      status: translate(t, "scheduler.columns.status") || "Status",
      actions: translate(t, "scheduler.columns.actions") || "Actions",
    }),
    [t]
  );

  const selectedIds = selectedJobs.map((job) => job.id).filter(Boolean) as (
    | number
    | string
  )[];

  /**
   * Mark jobs as being updated
   */
  const markUpdating = useCallback((ids: (number | string)[]) => {
    setUpdatingIds(new Set(ids));
  }, []);

  /**
   * Clear updating state
   */
  const clearUpdating = useCallback(
    (ids?: (number | string)[]) => {
      if (ids && ids.length > 0) {
        const newSet = new Set(updatingIds);
        ids.forEach((id) => newSet.delete(id));
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
    setSelectedJobs([]);
  }, []);

  /**
   * Handle refresh
   */
  const handleRefresh = useCallback(async () => {
    await onRefreshJobs();
  }, [onRefreshJobs]);

  /**
   * Handle toggle enabled from switch in column
   */
  const handleToggleEnabled = useCallback(
    async (jobId: number | string, enabled: boolean) => {
      setUpdatingIds((prev) => new Set(prev).add(jobId));
      try {
        const result = await onToggleJobEnabled(jobId, enabled);
        if (result.success) {
          toast.success(result.message);
          // Update local state
          const updatedJob = jobs.find((j) => j.id === jobId);
          if (updatedJob) {
            await updateJobs([{ ...updatedJob, isEnabled: enabled }]);
          }
        } else {
          toast.error(
            result.error ||
              translate(t, "scheduler.toast.statusError") ||
              "Failed to update job status"
          );
        }
      } finally {
        setUpdatingIds((prev) => {
          const newSet = new Set(prev);
          newSet.delete(jobId);
          return newSet;
        });
      }
    },
    [onToggleJobEnabled, jobs, updateJobs, t]
  );

  // Toast messages for bulk actions
  const toastMessages = useMemo(
    () => ({
      enabledMultiple:
        translate(t, "scheduler.toast.enabledMultiple") ||
        "Successfully enabled {count} job(s)",
      disabledMultiple:
        translate(t, "scheduler.toast.disabledMultiple") ||
        "Successfully disabled {count} job(s)",
      alreadyEnabled:
        translate(t, "scheduler.toast.alreadyEnabled") ||
        "Selected jobs are already enabled",
      alreadyDisabled:
        translate(t, "scheduler.toast.alreadyDisabled") ||
        "Selected jobs are already disabled",
      enableError:
        translate(t, "scheduler.toast.enableError") || "Failed to enable jobs",
      disableError:
        translate(t, "scheduler.toast.disableError") ||
        "Failed to disable jobs",
    }),
    [t]
  );

  // Get bulk action handlers
  const { handleDisable, handleEnable } = useSchedulerTableActions({
    jobs,
    updateJobs,
    markUpdating,
    clearUpdating,
    onRefresh: handleRefresh,
    toastMessages,
  });

  // Create columns with actions
  const columns = useMemo(
    () =>
      createSchedulerTableColumns({
        updatingIds,
        markUpdating,
        clearUpdating,
        onToggleEnabled: handleToggleEnabled,
        translations: columnTranslations,
        language,
      }).map((column) => {
        // Special handling for actions column to include JobActions
        if (column.id === "actions") {
          return {
            ...column,
            cell: ({ row }: { row: { original: ScheduledJob } }) => {
              const isRowUpdating = Boolean(
                row.original.id && updatingIds.has(row.original.id)
              );
              return (
                <div
                  className={`flex justify-center ${
                    isRowUpdating ? "opacity-60 pointer-events-none" : ""
                  }`}
                  onClick={(e) => e.stopPropagation()}
                >
                  <JobActions
                    job={row.original}
                    onUpdate={handleRefresh}
                    onJobUpdated={async (updatedJob) => {
                      // Only update local cache - no refetch needed
                      await updateJobs([updatedJob]);
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
    [
      updatingIds,
      updateJobs,
      handleRefresh,
      markUpdating,
      clearUpdating,
      handleToggleEnabled,
      columnTranslations,
      language,
    ]
  );

  // Memoize data
  const data = useMemo(() => jobs, [jobs]);

  return (
    <div className="h-full flex flex-col min-h-0 space-y-2">
      {/* Header Bar */}
      <div className="shrink-0">
        <SchedulerTableHeader page={page} tableInstance={tableInstance} />
      </div>

      {/* Controller Bar (includes Add Schedule button) */}
      <div className="shrink-0">
        <SchedulerTableController
          selectedIds={selectedIds}
          isUpdating={isUpdating}
          onClearSelection={handleClearSelection}
          onDisable={handleDisable}
          onEnable={handleEnable}
          onRefresh={handleRefresh}
          tableInstance={tableInstance}
          itemName={translate(t, "scheduler.itemName.singular") || "job"}
          columnLabels={{
            jobKey: columnTranslations.jobKey,
            name: columnTranslations.name,
            jobType: columnTranslations.type,
            schedule: columnTranslations.schedule,
            priority: columnTranslations.priority,
            isEnabled: columnTranslations.enabled,
            nextRunTime: columnTranslations.nextRun,
            lastRunTime: columnTranslations.lastRun,
            lastRunStatus: columnTranslations.status,
            actions: columnTranslations.actions,
          }}
        />
      </div>

      {/* Table */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <DataTable
          columns={columns}
          _data={data}
          tableInstanceHook={(table) => setTableInstance(table)}
          onRowSelectionChange={setSelectedJobs}
          renderToolbar={() => null}
          enableRowSelection={true}
          enableSorting={false}
        />
      </div>
    </div>
  );
}
