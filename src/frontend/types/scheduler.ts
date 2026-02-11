/**
 * Types for Scheduler Management
 */

// Lookup table types

export interface TaskFunction {
  id: number;
  key: string;
  functionPath: string;
  nameEn: string;
  nameAr: string;
  descriptionEn?: string | null;
  descriptionAr?: string | null;
  isActive: boolean;
}

export interface SchedulerJobType {
  id: number;
  code: string;
  nameEn: string;
  nameAr: string;
  descriptionEn?: string | null;
  descriptionAr?: string | null;
  sortOrder: number;
  isActive: boolean;
}

export interface SchedulerExecutionStatus {
  id: number;
  code: string;
  nameEn: string;
  nameAr: string;
  sortOrder: number;
  isActive: boolean;
}

export interface ScheduledJob {
  id: number;
  taskFunctionId: number;
  jobTypeId: number;
  // Computed from relationships (for backward compatibility)
  jobKey: string;
  jobFunction: string;
  jobType: string;
  // Names (from job override or task function)
  nameEn?: string | null;
  nameAr?: string | null;
  descriptionEn?: string | null;
  descriptionAr?: string | null;
  // Schedule settings
  intervalSeconds?: number | null;
  intervalMinutes?: number | null;
  intervalHours?: number | null;
  intervalDays?: number | null;
  cronExpression?: string | null;
  // Execution settings
  priority: number;
  maxInstances: number;
  misfireGraceTime: number;
  coalesce: boolean;
  // Status
  isEnabled: boolean;
  isActive: boolean;
  isPrimary: boolean;
  // Timestamps
  createdAt: string;
  updatedAt: string;
  lastRunAt?: string | null;  // Last time job was triggered
  createdById?: string | null;
  updatedById?: string | null;
  // Nested objects
  taskFunction?: TaskFunction | null;
  jobTypeRef?: SchedulerJobType | null;
  // Computed fields
  nextRunTime?: string | null;
  lastRunTime?: string | null;
  lastRunStatus?: string | null;
  // Current execution status (pending/running)
  currentExecutionStatus?: "pending" | "running" | null;
  currentExecutionId?: string | null;
}

export interface JobExecution {
  id: number;
  jobId: number;
  executionId: string;
  runId?: string | null;
  scheduledAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
  durationMs?: number | null;
  statusId: number;
  // Computed from status_ref for backward compatibility
  status: string;
  statusNameEn?: string | null;
  statusNameAr?: string | null;
  errorMessage?: string | null;
  errorTraceback?: string | null;
  resultSummary?: string | null;
  executorId?: string | null;
  hostName?: string | null;
  createdAt: string;
  // Nested object
  statusRef?: SchedulerExecutionStatus | null;
}

export interface SchedulerInstance {
  id: string;
  instanceName: string;
  hostName: string;
  processId: number;
  mode: "embedded" | "standalone";
  status: "starting" | "running" | "paused" | "stopping" | "stopped";
  lastHeartbeat: string;
  startedAt: string;
  stoppedAt?: string | null;
}

export interface SchedulerJobsResponse {
  items: ScheduledJob[];
  total: number;
  page: number;
  perPage: number;
  totalPages: number;
}

export interface TaskFunctionListResponse {
  items: TaskFunction[];
  total: number;
}

export interface SchedulerJobTypeListResponse {
  items: SchedulerJobType[];
  total: number;
}

export interface SchedulerExecutionStatusListResponse {
  items: SchedulerExecutionStatus[];
  total: number;
}

export interface JobExecutionsResponse {
  items: JobExecution[];
  total: number;
  page: number;
  perPage: number;
  totalPages: number;
}

export interface SchedulerStatusResponse {
  isRunning: boolean;
  totalJobs: number;
  enabledJobs: number;
  disabledJobs: number;
  activeInstances: SchedulerInstance[];
  nextScheduledJob?: ScheduledJob | null;
  recentExecutions: JobExecution[];
}

export interface JobActionResponse {
  success: boolean;
  message: string;
  jobId: number;
  action: string;
  executionId?: string | null;
  job?: ScheduledJob | null;  // Updated job data (for trigger action)
}

export interface CleanupResponse {
  success: boolean;
  deletedExecutions: number;
  deletedLocks: number;
  deletedInstances: number;
  message: string;
}

export type JobAction = "enable" | "disable" | "trigger" | "pause" | "resume";

export interface ScheduledJobCreate {
  taskFunctionId: number;
  jobTypeId: number;
  nameEn?: string;
  nameAr?: string;
  descriptionEn?: string;
  descriptionAr?: string;
  // Interval fields - required when jobTypeId is interval
  intervalSeconds?: number;
  intervalMinutes?: number;
  intervalHours?: number;
  intervalDays?: number;
  // Cron field - required when jobTypeId is cron
  cronExpression?: string;
  // Execution settings
  priority?: number;
  maxInstances?: number;
  misfireGraceTime?: number;
  coalesce?: boolean;
  isEnabled?: boolean;
  isPrimary?: boolean;
}

export interface ScheduledJobUpdate {
  taskFunctionId?: number;
  jobTypeId?: number;
  nameEn?: string;
  nameAr?: string;
  descriptionEn?: string;
  descriptionAr?: string;
  intervalSeconds?: number;
  intervalMinutes?: number;
  intervalHours?: number;
  intervalDays?: number;
  cronExpression?: string;
  priority?: number;
  maxInstances?: number;
  misfireGraceTime?: number;
  coalesce?: boolean;
  isEnabled?: boolean;
  isPrimary?: boolean;
}
