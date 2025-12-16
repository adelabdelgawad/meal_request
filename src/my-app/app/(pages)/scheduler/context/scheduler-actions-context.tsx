"use client";

import { createContext, useContext, ReactNode } from "react";
import type { ScheduledJob, ScheduledJobCreate, JobAction, TaskFunction, SchedulerJobType } from "@/types/scheduler";

/**
 * Result type for mutation operations
 */
interface MutationResult {
  success: boolean;
  message?: string;
  error?: string;
  data?: ScheduledJob;
  executionId?: string;
}

/**
 * Actions interface - mutations from the hook
 */
interface SchedulerActionsType {
  onToggleJobEnabled: (jobId: number | string, isEnabled: boolean) => Promise<MutationResult>;
  onTriggerJob: (jobId: number | string) => Promise<MutationResult>;
  onCreateJob: (data: ScheduledJobCreate) => Promise<MutationResult>;
  onUpdateJob: (jobId: number | string, data: Partial<ScheduledJob>) => Promise<MutationResult>;
  onDeleteJob: (jobId: number | string) => Promise<MutationResult>;
  onJobAction: (jobId: number | string, action: JobAction) => Promise<MutationResult>;
  updateJobs: (updatedJobs: ScheduledJob[]) => Promise<void>;
  onRefreshJobs: () => Promise<MutationResult>;
}

/**
 * Lookup data interface - pre-loaded reference data
 */
interface SchedulerLookupDataType {
  taskFunctions: TaskFunction[];
  jobTypes: SchedulerJobType[];
}

/**
 * UI State interface - shared component state
 */
interface SchedulerUIStateType {
  selectedJob: ScheduledJob | null;
  setSelectedJob: (job: ScheduledJob | null) => void;
  isCreateModalOpen: boolean;
  setIsCreateModalOpen: (open: boolean) => void;
  isEditModalOpen: boolean;
  setIsEditModalOpen: (open: boolean) => void;
  isViewModalOpen: boolean;
  setIsViewModalOpen: (open: boolean) => void;
  isConfirmDialogOpen: boolean;
  setIsConfirmDialogOpen: (open: boolean) => void;
  isAnyModalOpen: boolean;
}

/**
 * Combined context type
 */
type SchedulerContextType = SchedulerActionsType & SchedulerUIStateType & SchedulerLookupDataType;

const SchedulerContext = createContext<SchedulerContextType | null>(null);

interface SchedulerProviderProps {
  children: ReactNode;
  actions: SchedulerActionsType;
  taskFunctions: TaskFunction[];
  jobTypes: SchedulerJobType[];
  uiState: SchedulerUIStateType;
}

export function SchedulerProvider({ children, actions, taskFunctions, jobTypes, uiState }: SchedulerProviderProps) {
  const value: SchedulerContextType = {
    // Actions from hook
    ...actions,
    // Lookup data
    taskFunctions,
    jobTypes,
    // UI State (passed from parent)
    ...uiState,
  };

  return (
    <SchedulerContext.Provider value={value}>
      {children}
    </SchedulerContext.Provider>
  );
}

export function useSchedulerContext() {
  const context = useContext(SchedulerContext);
  if (!context) {
    throw new Error("useSchedulerContext must be used within SchedulerProvider");
  }
  return context;
}

// Convenience hooks for specific data

/**
 * Hook to access scheduler actions only
 */
export function useSchedulerActions() {
  const {
    onToggleJobEnabled,
    onTriggerJob,
    onCreateJob,
    onUpdateJob,
    onDeleteJob,
    onJobAction,
    updateJobs,
    onRefreshJobs,
  } = useSchedulerContext();

  return {
    onToggleJobEnabled,
    onTriggerJob,
    onCreateJob,
    onUpdateJob,
    onDeleteJob,
    onJobAction,
    updateJobs,
    onRefreshJobs,
  };
}

/**
 * Hook to access UI state only
 */
export function useSchedulerUIState() {
  const {
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
  } = useSchedulerContext();

  return {
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
  };
}

/**
 * Hook to access lookup data only
 */
export function useSchedulerLookupData() {
  const { taskFunctions, jobTypes } = useSchedulerContext();
  return { taskFunctions, jobTypes };
}
