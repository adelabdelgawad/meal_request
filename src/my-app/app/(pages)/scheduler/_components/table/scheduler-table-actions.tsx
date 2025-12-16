"use client";

import { toast } from "sonner";
import { clientApi } from "@/lib/http/axios-client";
import type { ScheduledJob } from "@/types/scheduler";

interface ToastTranslations {
  enabledMultiple: string;
  disabledMultiple: string;
  alreadyEnabled: string;
  alreadyDisabled: string;
  enableError: string;
  disableError: string;
}

interface SchedulerTableActionsProps {
  jobs: ScheduledJob[];
  updateJobs: (updatedJobs: ScheduledJob[]) => Promise<void>;
  markUpdating: (ids: (number | string)[]) => void;
  clearUpdating: (ids?: (number | string)[]) => void;
  onRefresh: () => Promise<void> | void;
  toastMessages?: ToastTranslations;
}

// Default messages (fallback when translations not provided)
const defaultMessages: ToastTranslations = {
  enabledMultiple: "Successfully enabled {count} job(s)",
  disabledMultiple: "Successfully disabled {count} job(s)",
  alreadyEnabled: "Selected jobs are already enabled",
  alreadyDisabled: "Selected jobs are already disabled",
  enableError: "Failed to enable jobs",
  disableError: "Failed to disable jobs",
};

/**
 * Handles bulk action operations for scheduled jobs
 */
export function useSchedulerTableActions({
  jobs,
  updateJobs,
  markUpdating,
  clearUpdating,
  onRefresh,
  toastMessages,
}: SchedulerTableActionsProps) {
  const messages = toastMessages || defaultMessages;

  // Handle disable jobs (bulk)
  const handleDisable = async (ids: (number | string)[]) => {
    try {
      if (ids.length === 0) return;

      // Filter to only enabled jobs (ones that need to be disabled)
      // Also exclude primary jobs
      const enabledJobsToDisable = jobs.filter(
        (j) => j.id && ids.includes(j.id) && j.isEnabled && !j.isPrimary
      );

      if (enabledJobsToDisable.length === 0) {
        toast.info(messages.alreadyDisabled);
        return;
      }

      const jobIdsToDisable = enabledJobsToDisable.map((j) => j.id!);

      // Mark jobs as updating (show loading spinner)
      markUpdating(jobIdsToDisable);

      // Call API for each job
      const updatedJobs: ScheduledJob[] = [];
      for (const jobId of jobIdsToDisable) {
        try {
          const response = await clientApi.post<{ message: string }>(
            `/scheduler/jobs/${jobId}/action`,
            { action: "disable" }
          );
          if (response.ok) {
            const job = jobs.find((j) => j.id === jobId);
            if (job) {
              updatedJobs.push({ ...job, isEnabled: false });
            }
          }
        } catch (error) {
          console.error(`Failed to disable job ${jobId}:`, error);
        }
      }

      // Update local state with returned data
      if (updatedJobs.length > 0) {
        await updateJobs(updatedJobs);
        // Wait for state to update before clearing loading spinner
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      // Show success toast with localized message
      const successMsg = messages.disabledMultiple.replace(
        "{count}",
        String(updatedJobs.length)
      );
      toast.success(successMsg);

      // Refresh to get latest data
      await onRefresh();
    } catch (error: unknown) {
      console.error("Failed to disable jobs:", error);
      toast.error(messages.disableError);
    } finally {
      clearUpdating();
    }
  };

  // Handle enable jobs (bulk)
  const handleEnable = async (ids: (number | string)[]) => {
    try {
      if (ids.length === 0) return;

      // Filter to only disabled jobs (ones that need to be enabled)
      // Also exclude primary jobs (they're always enabled)
      const disabledJobsToEnable = jobs.filter(
        (j) => j.id && ids.includes(j.id) && !j.isEnabled && !j.isPrimary
      );

      if (disabledJobsToEnable.length === 0) {
        toast.info(messages.alreadyEnabled);
        return;
      }

      const jobIdsToEnable = disabledJobsToEnable.map((j) => j.id!);

      // Mark jobs as updating (show loading spinner)
      markUpdating(jobIdsToEnable);

      // Call API for each job
      const updatedJobs: ScheduledJob[] = [];
      for (const jobId of jobIdsToEnable) {
        try {
          const response = await clientApi.post<{ message: string }>(
            `/scheduler/jobs/${jobId}/action`,
            { action: "enable" }
          );
          if (response.ok) {
            const job = jobs.find((j) => j.id === jobId);
            if (job) {
              updatedJobs.push({ ...job, isEnabled: true });
            }
          }
        } catch (error) {
          console.error(`Failed to enable job ${jobId}:`, error);
        }
      }

      // Update local state with returned data
      if (updatedJobs.length > 0) {
        await updateJobs(updatedJobs);
        // Wait for state to update before clearing loading spinner
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      // Show success toast with localized message
      const successMsg = messages.enabledMultiple.replace(
        "{count}",
        String(updatedJobs.length)
      );
      toast.success(successMsg);

      // Refresh to get latest data
      await onRefresh();
    } catch (error: unknown) {
      console.error("Failed to enable jobs:", error);
      toast.error(messages.enableError);
    } finally {
      clearUpdating();
    }
  };

  return {
    handleDisable,
    handleEnable,
  };
}
