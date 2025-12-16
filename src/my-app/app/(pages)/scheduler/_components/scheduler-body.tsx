"use client";

/**
 * SchedulerBody - Main client component wrapper
 *
 * This component:
 * 1. Uses the useSchedulerJobs hook for data and mutations
 * 2. Wraps children with SchedulerProvider for context
 * 3. Passes actions to context for child components to use
 */

import React from "react";
import { useSchedulerJobs } from "@/hooks/use-scheduler-jobs";
import { SchedulerProvider } from "../context/scheduler-actions-context";
import { StatusPanel } from "./sidebar/status-panel";
import SchedulerTableView from "./table/scheduler-table";
import LoadingSkeleton from "@/components/loading-skeleton";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Pagination } from "@/components/data-table/table/pagination";
import { useLanguage, translate } from "@/hooks/use-language";
import type {
  SchedulerJobsResponse,
  SchedulerStatusResponse,
  TaskFunction,
  SchedulerJobType,
  ScheduledJob,
} from "@/types/scheduler";

interface SchedulerBodyProps {
  initialData: SchedulerJobsResponse | null;
  initialStatus: SchedulerStatusResponse | null;
  taskFunctions: TaskFunction[];
  jobTypes: SchedulerJobType[];
}

export function SchedulerBody({
  initialData,
  initialStatus,
  taskFunctions,
  jobTypes
}: SchedulerBodyProps) {
  const { t } = useLanguage();

  // UI state for modals (lifted up to control SWR polling)
  const [selectedJob, setSelectedJob] = React.useState<ScheduledJob | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = React.useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = React.useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = React.useState(false);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = React.useState(false);

  // Track if any modal is open (including confirmation dialogs to pause SWR polling)
  const isAnyModalOpen = isCreateModalOpen || isEditModalOpen || isViewModalOpen || isConfirmDialogOpen;

  // Use the custom hook for all data and mutations
  const {
    jobs,
    total,
    totalPages,
    status,
    enabledCount,
    disabledCount,
    page,
    limit,
    isLoading,
    error,
    createJob,
    updateJob,
    deleteJob,
    toggleJobEnabled,
    triggerJob,
    jobAction,
    updateJobsInCache,
    refresh,
    mutateJobs,
  } = useSchedulerJobs({ initialData, initialStatus, isAnyModalOpen });

  // Create actions object for context
  const actions = {
    onToggleJobEnabled: toggleJobEnabled,
    onTriggerJob: triggerJob,
    onCreateJob: createJob,
    onUpdateJob: updateJob,
    onDeleteJob: deleteJob,
    onJobAction: jobAction,
    updateJobs: updateJobsInCache,
    onRefreshJobs: refresh,
  };

  // Error state with retry button
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-red-500 mb-2">
            {translate(t, "scheduler.error.loadJobs") || "Failed to load scheduled jobs"}
          </div>
          <div className="text-gray-600 text-sm mb-4">{error.message}</div>
          <button
            onClick={() => mutateJobs()}
            className="px-4 py-2 bg-blue-500 text-white hover:bg-blue-600"
          >
            {translate(t, "common.retry") || "Retry"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <SchedulerProvider
      actions={actions}
      taskFunctions={taskFunctions}
      jobTypes={jobTypes}
      uiState={{
        selectedJob,
        setSelectedJob,
        isCreateModalOpen,
        setIsCreateModalOpen,
        isEditModalOpen,
        setIsEditModalOpen,
        isViewModalOpen,
        setIsViewModalOpen,
        isConfirmDialogOpen,
        setIsConfirmDialogOpen,
        isAnyModalOpen,
      }}
    >
      <div className="relative h-full flex gap-3 bg-muted/30 min-h-0 pt-1.5">
        {/* Loading Overlay */}
        {isLoading && <LoadingSkeleton />}

        {/* Status Panel */}
        <StatusPanel
          totalJobs={enabledCount + disabledCount}
          enabledCount={enabledCount}
          disabledCount={disabledCount}
          isRunning={status?.isRunning ?? false}
          activeInstances={status?.activeInstances ?? []}
          recentExecutions={status?.recentExecutions ?? []}
        />

        {/* Main Content */}
        <ErrorBoundary>
          <div className="flex-1 flex flex-col min-h-0 min-w-0 space-y-2">
            {/* Table */}
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <SchedulerTableView jobs={jobs} page={page} />
            </div>

            {/* Pagination */}
            <div className="shrink-0 bg-card">
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                pageSize={limit}
                totalItems={total}
              />
            </div>
          </div>
        </ErrorBoundary>
      </div>
    </SchedulerProvider>
  );
}

export default SchedulerBody;
