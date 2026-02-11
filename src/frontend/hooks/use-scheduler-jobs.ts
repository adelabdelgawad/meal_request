"use client";

/**
 * Custom hook for managing scheduler jobs data and mutations
 * Follows the SWR pattern with proper cache updates (no full refetch)
 */

import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { clientApi } from "@/lib/http/axios-client";
import type {
  SchedulerJobsResponse,
  SchedulerStatusResponse,
  ScheduledJob,
  ScheduledJobCreate,
  JobAction,
  JobActionResponse,
} from "@/types/scheduler";

interface UseSchedulerJobsOptions {
  initialData?: SchedulerJobsResponse | null;
  initialStatus?: SchedulerStatusResponse | null;
  isAnyModalOpen?: boolean;
}

interface MutationResult {
  success: boolean;
  message?: string;
  error?: string;
  data?: ScheduledJob;
  executionId?: string | number;
}

/**
 * Fetcher for jobs data
 */
const jobsFetcher = async (url: string): Promise<SchedulerJobsResponse> => {
  const response = await clientApi.get<SchedulerJobsResponse>(url);
  if (!response.ok) {
    throw new Error(response.error || "Failed to fetch jobs");
  }
  return response.data;
};

/**
 * Fetcher for status data
 */
const statusFetcher = async (url: string): Promise<SchedulerStatusResponse> => {
  const response = await clientApi.get<SchedulerStatusResponse>(url);
  if (!response.ok) {
    throw new Error(response.error || "Failed to fetch status");
  }
  return response.data;
};

export function useSchedulerJobs(options: UseSchedulerJobsOptions = {}) {
  const { initialData, initialStatus, isAnyModalOpen = false } = options;
  const searchParams = useSearchParams();

  // Get polling interval from environment variable (default: 3 seconds)
  const pollInterval = Number(process.env.NEXT_PUBLIC_SCHEDULER_POLL_INTERVAL) || 3000;

  // Read URL parameters
  const page = Number(searchParams?.get("page") || "1");
  const limit = Number(searchParams?.get("limit") || "10");
  const isEnabled = searchParams?.get("is_enabled") || "";
  const jobType = searchParams?.get("job_type") || "";

  // Build API URL with current filters
  const params = new URLSearchParams();
  params.append("skip", ((page - 1) * limit).toString());
  params.append("limit", limit.toString());
  if (isEnabled) {
    params.append("is_enabled", isEnabled);
  }
  if (jobType) {
    params.append("job_type", jobType);
  }

  const jobsApiUrl = `/scheduler/jobs?${params.toString()}`;
  const statusApiUrl = `/scheduler/status`;

  // SWR hook for jobs with DYNAMIC refresh interval
  const {
    data: jobsData,
    mutate: mutateJobs,
    isLoading: isLoadingJobs,
    isValidating: isValidatingJobs,
    error: jobsError,
  } = useSWR<SchedulerJobsResponse>(jobsApiUrl, jobsFetcher, {
    fallbackData: initialData ?? undefined,
    keepPreviousData: true,
    revalidateOnMount: true, // ✅ FIX: Revalidate on mount to trigger refreshInterval check
    revalidateIfStale: true,
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    // ✅ FIX: Use a function for dynamic refresh interval
    // SWR will call this function to get the interval value dynamically
    refreshInterval: (latestData) => {
      // Don't poll if any modal is open to prevent re-renders that close dialogs
      if (isAnyModalOpen) {
        return 0;
      }

      // Check if there are any pending/running jobs in the latest data
      const hasPending = latestData?.items?.some(
        (job) =>
          job.currentExecutionStatus === "pending" ||
          job.currentExecutionStatus === "running"
      );
      // Poll at configured interval if there are pending jobs, otherwise don't poll
      return hasPending ? pollInterval : 0;
    },
    refreshWhenHidden: true, // Continue polling even when tab is hidden
    refreshWhenOffline: false,
  });

  // SWR hook for status with same dynamic polling
  const {
    data: statusData,
    mutate: mutateStatus,
    isLoading: isLoadingStatus,
  } = useSWR<SchedulerStatusResponse>(statusApiUrl, statusFetcher, {
    fallbackData: initialStatus ?? undefined,
    revalidateOnMount: false,
    revalidateIfStale: true,
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    // ✅ FIX: Poll status when jobs are being polled (use same interval)
    refreshInterval: (latestData) => {
      // Don't poll if any modal is open
      if (isAnyModalOpen) {
        return 0;
      }

      // Poll status when there are recent executions or jobs are running
      const hasRecentExecutions =
        (latestData?.recentExecutions?.length ?? 0) > 0;
      const jobsHavePending = jobsData?.items?.some(
        (job) =>
          job.currentExecutionStatus === "pending" ||
          job.currentExecutionStatus === "running"
      );
      const interval = hasRecentExecutions || jobsHavePending ? pollInterval : 0;
      return interval;
    },
    refreshWhenHidden: true,
    refreshWhenOffline: false,
  });

  const jobs = jobsData?.items ?? [];
  const total = jobsData?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  /**
   * Update specific jobs in the cache without refetching
   */
  const updateJobsInCache = async (updatedJobs: ScheduledJob[]) => {
    await mutateJobs(
      (currentData: SchedulerJobsResponse | undefined) => {
        if (!currentData) return currentData;

        const updatedMap = new Map(updatedJobs.map((j) => [j.id, j]));

        return {
          ...currentData,
          items: currentData.items.map((job) =>
            updatedMap.has(job.id) ? updatedMap.get(job.id)! : job
          ),
        };
      },
      { revalidate: false }
    );
  };

  /**
   * CREATE - Add new scheduled job
   */
  const createJob = async (
    data: ScheduledJobCreate
  ): Promise<MutationResult> => {
    try {
      const response = await clientApi.post<ScheduledJob>(
        `/scheduler/jobs`,
        data
      );

      if (!response.ok) {
        return {
          success: false,
          error: response.message || response.error || "Failed to create job",
        };
      }

      // Update cache with new job (no refetch)
      await mutateJobs(
        (currentData) => {
          if (!currentData) return currentData;
          return {
            ...currentData,
            items: [response.data, ...currentData.items],
            total: currentData.total + 1,
          };
        },
        { revalidate: false }
      );

      // Refresh status to update counts
      await mutateStatus();

      return {
        success: true,
        message: "Job created successfully",
        data: response.data,
      };
    } catch (error) {
      const err = error as Error;
      return {
        success: false,
        error: err.message || "Failed to create job",
      };
    }
  };

  /**
   * UPDATE - Modify existing job
   */
  const updateJob = async (
    jobId: number | string,
    data: Partial<ScheduledJob>
  ): Promise<MutationResult> => {
    try {
      const response = await clientApi.put<ScheduledJob>(
        `/scheduler/jobs/${jobId}`,
        data
      );

      if (!response.ok) {
        return {
          success: false,
          error: response.message || response.error || "Failed to update job",
        };
      }

      // Update cache with modified job (no refetch)
      await updateJobsInCache([response.data]);

      return {
        success: true,
        message: "Job updated successfully",
        data: response.data,
      };
    } catch (error) {
      const err = error as Error;
      return {
        success: false,
        error: err.message || "Failed to update job",
      };
    }
  };

  /**
   * DELETE - Remove job
   */
  const deleteJob = async (jobId: number | string): Promise<MutationResult> => {
    try {
      const response = await clientApi.delete(`/scheduler/jobs/${jobId}`);

      if (!response.ok) {
        return {
          success: false,
          error: response.message || response.error || "Failed to delete job",
        };
      }

      // Remove from cache (no refetch)
      await mutateJobs(
        (currentData) => {
          if (!currentData) return currentData;
          return {
            ...currentData,
            items: currentData.items.filter((j) => j.id !== jobId),
            total: currentData.total - 1,
          };
        },
        { revalidate: false }
      );

      // Refresh status to update counts
      await mutateStatus();

      return {
        success: true,
        message: "Job deleted successfully",
      };
    } catch (error) {
      const err = error as Error;
      return {
        success: false,
        error: err.message || "Failed to delete job",
      };
    }
  };

  /**
   * Toggle job enabled/disabled status
   */
  const toggleJobEnabled = async (
    jobId: number | string,
    isEnabled: boolean
  ): Promise<MutationResult> => {
    try {
      const response = await clientApi.post<JobActionResponse>(
        `/scheduler/jobs/${jobId}/action`,
        { action: isEnabled ? "enable" : "disable" }
      );

      if (!response.ok) {
        return {
          success: false,
          error:
            response.message || response.error || "Failed to update job status",
        };
      }

      // Update the job in cache
      const existingJob = jobs.find((j) => j.id === jobId);
      if (existingJob) {
        await updateJobsInCache([{ ...existingJob, isEnabled }]);
      }

      // Refresh status to update counts
      await mutateStatus();

      return {
        success: true,
        message: `Job ${isEnabled ? "enabled" : "disabled"} successfully`,
      };
    } catch (error) {
      const err = error as Error;
      return {
        success: false,
        error: err.message || "Failed to update job status",
      };
    }
  };

  /**
   * Trigger job execution
   */
  const triggerJob = async (jobId: number | string): Promise<MutationResult> => {
    try {
      // Optimistic update: Set job to running state immediately
      await mutateJobs(
        (currentData: SchedulerJobsResponse | undefined) => {
          if (!currentData) return currentData;

          return {
            ...currentData,
            items: currentData.items.map((job) =>
              job.id === jobId
                ? {
                    ...job,
                    currentExecutionStatus: "running" as const,
                    lastRunAt: new Date().toISOString(),
                    lastRunTime: new Date().toISOString(),
                  }
                : job
            ),
          };
        },
        { revalidate: false } // Don't revalidate immediately
      );

      const response = await clientApi.post<JobActionResponse>(
        `/scheduler/jobs/${jobId}/action`,
        { action: "trigger" }
      );

      if (!response.ok) {
        // Revert optimistic update on error
        await mutateJobs();

        return {
          success: false,
          error: response.message || response.error || "Failed to trigger job",
        };
      }

      // Update cache with returned job data
      if (response.data?.job) {
        await mutateJobs(
          (currentData: SchedulerJobsResponse | undefined) => {
            if (!currentData) return currentData;

            return {
              ...currentData,
              items: currentData.items.map((job) =>
                job.id === jobId ? response.data.job! : job
              ),
            };
          },
          { revalidate: false }
        );
      }

      // Refresh status to show recent execution
      await mutateStatus();

      return {
        success: true,
        message: response.data?.message || "Job triggered successfully",
        executionId: response.data?.executionId ?? undefined,
        data: response.data?.job ?? undefined,
      };
    } catch (error) {
      // Revert optimistic update on error
      await mutateJobs();

      const err = error as Error;
      return {
        success: false,
        error: err.message || "Failed to trigger job",
      };
    }
  };

  /**
   * Perform any action on a job
   */
  const jobAction = async (
    jobId: number | string,
    action: JobAction
  ): Promise<MutationResult> => {
    try {
      const response = await clientApi.post<JobActionResponse>(
        `/scheduler/jobs/${jobId}/action`,
        { action }
      );

      if (!response.ok) {
        return {
          success: false,
          error:
            response.message || response.error || `Failed to ${action} job`,
        };
      }

      // Refresh both jobs and status
      await mutateJobs();
      await mutateStatus();

      return {
        success: true,
        message: `Job ${action} successfully`,
        executionId: response.data?.executionId ?? undefined,
      };
    } catch (error) {
      const err = error as Error;
      return {
        success: false,
        error: err.message || `Failed to ${action} job`,
      };
    }
  };

  /**
   * Manual refresh of all data
   */
  const refresh = async (): Promise<MutationResult> => {
    await mutateJobs();
    await mutateStatus();
    return {
      success: true,
      message: "Data refreshed",
    };
  };

  return {
    // Data
    jobs,
    total,
    totalPages,
    status: statusData ?? null,
    enabledCount: statusData?.enabledJobs ?? 0,
    disabledCount: statusData?.disabledJobs ?? 0,

    // Pagination
    page,
    limit,

    // States
    isLoading: isLoadingJobs || isLoadingStatus,
    isValidating: isValidatingJobs,
    error: jobsError,

    // Mutations
    createJob,
    updateJob,
    deleteJob,
    toggleJobEnabled,
    triggerJob,
    jobAction,

    // Cache helpers
    updateJobsInCache,

    // Manual refresh
    refresh,
    mutateJobs,
    mutateStatus,
  };
}
