"use server";

/**
 * Server Actions for Scheduler Management
 * These functions run on the server and communicate with the backend API
 */

import { serverApi } from "@/lib/http/axios-server";
import type {
  SchedulerJobsResponse,
  SchedulerStatusResponse,
  ScheduledJob,
  TaskFunction,
  SchedulerJobType,
  SchedulerExecutionStatus,
  TaskFunctionListResponse,
  SchedulerJobTypeListResponse,
  SchedulerExecutionStatusListResponse,
} from "@/types/scheduler";

/**
 * Fetch scheduled jobs list with pagination and filtering
 */
export async function getScheduledJobs(
  limit: number = 10,
  skip: number = 0,
  filters?: {
    is_enabled?: string;
    job_type?: string;
  }
): Promise<SchedulerJobsResponse | null> {
  try {
    const params: Record<string, string | number> = {
      per_page: limit,
      page: Math.floor(skip / limit) + 1,
    };

    // Add filters if provided
    if (filters?.is_enabled) {
      params.is_enabled = filters.is_enabled;
    }
    if (filters?.job_type) {
      params.job_type = filters.job_type;
    }

    const result = await serverApi.get<SchedulerJobsResponse>("/scheduler/jobs", {
      params,
      useVersioning: true, // Requests /api/v1/scheduler/jobs
    });

    if (result.ok && result.data) {
      return result.data;
    }

    if (!result.ok) {
      console.error("Failed to fetch scheduled jobs:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getScheduledJobs:", error);
    return null;
  }
}

/**
 * Fetch scheduler status
 */
export async function getSchedulerStatus(): Promise<SchedulerStatusResponse | null> {
  try {
    const result = await serverApi.get<SchedulerStatusResponse>("/scheduler/status", {
      useVersioning: true,
    });

    if (result.ok && result.data) {
      return result.data;
    }

    if (!result.ok) {
      console.error("Failed to fetch scheduler status:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getSchedulerStatus:", error);
    return null;
  }
}

/**
 * Fetch a single scheduled job by ID
 */
export async function getScheduledJobById(
  jobId: string
): Promise<ScheduledJob | null> {
  try {
    const result = await serverApi.get<ScheduledJob>(`/scheduler/jobs/${jobId}`, {
      useVersioning: true,
    });

    if (result.ok && result.data) {
      return result.data;
    }

    if (!result.ok) {
      console.error("Failed to fetch scheduled job:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getScheduledJobById:", error);
    return null;
  }
}

/**
 * Fetch available task functions
 */
export async function getTaskFunctions(): Promise<TaskFunction[]> {
  try {
    const result = await serverApi.get<TaskFunctionListResponse>(
      "/scheduler/task-functions",
      {
        useVersioning: true,
      }
    );

    if (result.ok && result.data) {
      return result.data.items;
    }

    if (!result.ok) {
      console.error("Failed to fetch task functions:", result.error);
    }
    return [];
  } catch (error) {
    console.error("Error in getTaskFunctions:", error);
    return [];
  }
}

/**
 * Fetch available job types
 */
export async function getJobTypes(): Promise<SchedulerJobType[]> {
  try {
    const result = await serverApi.get<SchedulerJobTypeListResponse>(
      "/scheduler/job-types",
      {
        useVersioning: true,
      }
    );

    if (result.ok && result.data) {
      return result.data.items;
    }

    if (!result.ok) {
      console.error("Failed to fetch job types:", result.error);
    }
    return [];
  } catch (error) {
    console.error("Error in getJobTypes:", error);
    return [];
  }
}

/**
 * Fetch available execution statuses
 */
export async function getExecutionStatuses(): Promise<SchedulerExecutionStatus[]> {
  try {
    const result = await serverApi.get<SchedulerExecutionStatusListResponse>(
      "/scheduler/execution-statuses",
      {
        useVersioning: true,
      }
    );

    if (result.ok && result.data) {
      return result.data.items;
    }

    if (!result.ok) {
      console.error("Failed to fetch execution statuses:", result.error);
    }
    return [];
  } catch (error) {
    console.error("Error in getExecutionStatuses:", error);
    return [];
  }
}
