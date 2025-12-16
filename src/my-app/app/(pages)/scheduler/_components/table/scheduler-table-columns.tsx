"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { format, formatDistanceToNow } from "date-fns";
import { ar, enUS } from "date-fns/locale";
import type { ScheduledJob } from "@/types/scheduler";
import { Clock, Calendar, CheckCircle, XCircle, AlertCircle, Loader2, Lock } from "lucide-react";
import { Switch } from "@/components/ui/switch";

interface CreateColumnsParams {
  updatingIds: Set<number | string>;
  markUpdating: (ids: (number | string)[]) => void;
  clearUpdating: (ids?: (number | string)[]) => void;
  onToggleEnabled?: (jobId: number | string, enabled: boolean) => Promise<void>;
  translations: {
    jobKey: string;
    name: string;
    type: string;
    schedule: string;
    priority: string;
    enabled: string;
    nextRun: string;
    lastRun: string;
    status: string;
    actions: string;
  };
  language: string;
}

/**
 * Format schedule display based on job type
 */
function formatSchedule(job: ScheduledJob): string {
  if (job.jobType === "cron" && job.cronExpression) {
    return job.cronExpression;
  }

  const parts: string[] = [];
  if (job.intervalDays) parts.push(`${job.intervalDays}d`);
  if (job.intervalHours) parts.push(`${job.intervalHours}h`);
  if (job.intervalMinutes) parts.push(`${job.intervalMinutes}m`);
  if (job.intervalSeconds) parts.push(`${job.intervalSeconds}s`);

  return parts.length > 0 ? parts.join(" ") : "-";
}

/**
 * Get status badge variant and icon
 */
function getStatusBadge(status: string | null | undefined) {
  switch (status) {
    case "completed":
      return {
        variant: "default" as const,
        icon: CheckCircle,
        className: "bg-green-100 text-green-800 border-green-200",
      };
    case "running":
      return {
        variant: "secondary" as const,
        icon: Loader2,
        className: "bg-blue-100 text-blue-800 border-blue-200 animate-pulse",
      };
    case "failed":
      return {
        variant: "destructive" as const,
        icon: XCircle,
        className: "bg-red-100 text-red-800 border-red-200",
      };
    case "queued":
      return {
        variant: "outline" as const,
        icon: Clock,
        className: "bg-yellow-100 text-yellow-800 border-yellow-200",
      };
    case "skipped":
    case "cancelled":
      return {
        variant: "outline" as const,
        icon: AlertCircle,
        className: "bg-gray-100 text-gray-600 border-gray-200",
      };
    default:
      return {
        variant: "outline" as const,
        icon: AlertCircle,
        className: "bg-gray-100 text-gray-500 border-gray-200",
      };
  }
}

export function createSchedulerTableColumns({
  updatingIds,
  onToggleEnabled,
  translations,
  language,
}: CreateColumnsParams): ColumnDef<ScheduledJob>[] {
  const locale = language === "ar" ? ar : enUS;

  return [
    {
      accessorKey: "jobKey",
      header: () => (
        <div className="text-center">{translations.jobKey}</div>
      ),
      size: 180,
      minSize: 150,
      maxSize: 220,
      cell: ({ row }) => (
        <div className="font-mono text-sm text-muted-foreground text-center">
          {row.original.jobKey}
        </div>
      ),
    },
    {
      accessorKey: "name",
      header: () => (
        <div className="text-center">{translations.name}</div>
      ),
      size: 220,
      minSize: 200,
      maxSize: 350,
      cell: ({ row }) => {
        const name = language === "ar" ? row.original.nameAr : row.original.nameEn;
        const description =
          language === "ar" ? row.original.descriptionAr : row.original.descriptionEn;
        const executionStatus = row.original.currentExecutionStatus;

        return (
          <div className="flex flex-col items-center text-center">
            <div className="flex items-center gap-2">
              <span className="font-medium">{name}</span>
              {executionStatus && (
                <Badge
                  variant="secondary"
                  className={`text-[10px] px-1.5 py-0 ${
                    executionStatus === "pending"
                      ? "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400"
                      : "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400"
                  }`}
                >
                  {executionStatus === "pending" && (
                    <Clock className="h-2.5 w-2.5 inline me-1" />
                  )}
                  {executionStatus === "running" && (
                    <Loader2 className="h-2.5 w-2.5 animate-spin inline me-1" />
                  )}
                  {executionStatus}
                </Badge>
              )}
            </div>
            {description && (
              <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                {description}
              </span>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "jobType",
      header: () => (
        <div className="text-center">{translations.type}</div>
      ),
      size: 100,
      minSize: 90,
      maxSize: 120,
      cell: ({ row }) => {
        const isInterval = row.original.jobType === "interval";
        return (
          <div className="flex justify-center">
            <Badge variant="outline" className="flex items-center gap-1 w-fit">
              {isInterval ? (
                <Clock className="h-3 w-3" />
              ) : (
                <Calendar className="h-3 w-3" />
              )}
              {row.original.jobType}
            </Badge>
          </div>
        );
      },
    },
    {
      accessorKey: "schedule",
      header: () => (
        <div className="text-center">{translations.schedule}</div>
      ),
      size: 140,
      minSize: 120,
      maxSize: 180,
      cell: ({ row }) => (
        <div className="text-center">
          <span className="font-mono text-sm">{formatSchedule(row.original)}</span>
        </div>
      ),
    },
    {
      accessorKey: "priority",
      header: () => (
        <div className="text-center">{translations.priority}</div>
      ),
      size: 90,
      minSize: 80,
      maxSize: 110,
      cell: ({ row }) => (
        <div className="flex justify-center">
          <Badge
            variant={row.original.priority > 5 ? "default" : "secondary"}
            className="w-8 justify-center"
          >
            {row.original.priority}
          </Badge>
        </div>
      ),
    },
    {
      accessorKey: "isEnabled",
      header: () => (
        <div className="text-center">{translations.enabled}</div>
      ),
      size: 90,
      minSize: 80,
      maxSize: 110,
      cell: ({ row }) => {
        const isUpdating = updatingIds.has(row.original.id);
        const isPrimary = row.original.isPrimary;

        // Show lock icon for primary jobs (can't be toggled)
        if (isPrimary) {
          return (
            <div className="flex justify-center items-center gap-1">
              {row.original.isEnabled ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-gray-400" />
              )}
              <Lock className="h-3 w-3 text-muted-foreground" />
            </div>
          );
        }

        // Show switch for non-primary jobs
        return (
          <div className="flex justify-center">
            {isUpdating ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : (
              <Switch
                checked={row.original.isEnabled}
                onCheckedChange={(checked) => {
                  if (onToggleEnabled) {
                    onToggleEnabled(row.original.id, checked);
                  }
                }}
                className="data-[state=checked]:bg-green-600"
              />
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "nextRunTime",
      header: () => (
        <div className="text-center">{translations.nextRun}</div>
      ),
      size: 140,
      minSize: 120,
      maxSize: 180,
      cell: ({ row }) => {
        const nextRun = row.original.nextRunTime;
        if (!nextRun) {
          return <div className="text-center text-muted-foreground">-</div>;
        }
        try {
          // Parse UTC timestamp and convert to local timezone
          const date = new Date(nextRun);
          const localTime = format(date, "MMM d, HH:mm", { locale });
          const fullDateTime = format(date, "PPp", { locale }); // Full date and time for tooltip

          return (
            <div className="flex flex-col text-sm text-center" title={fullDateTime}>
              <span>{localTime}</span>
              <span className="text-xs text-muted-foreground">
                {formatDistanceToNow(date, { addSuffix: true, locale })}
              </span>
            </div>
          );
        } catch {
          return <div className="text-center text-muted-foreground">-</div>;
        }
      },
    },
    {
      accessorKey: "lastRunTime",
      header: () => (
        <div className="text-center">{translations.lastRun}</div>
      ),
      size: 140,
      minSize: 120,
      maxSize: 180,
      cell: ({ row }) => {
        const lastRun = row.original.lastRunTime;
        if (!lastRun) {
          return <div className="text-center text-muted-foreground">Never</div>;
        }
        try {
          // Parse UTC timestamp and convert to local timezone
          const date = new Date(lastRun);
          const localTime = format(date, "MMM d, HH:mm", { locale });
          const fullDateTime = format(date, "PPp", { locale }); // Full date and time for tooltip

          return (
            <div className="flex flex-col text-sm text-center" title={fullDateTime}>
              <span>{localTime}</span>
              <span className="text-xs text-muted-foreground">
                {formatDistanceToNow(date, { addSuffix: true, locale })}
              </span>
            </div>
          );
        } catch {
          return <div className="text-center text-muted-foreground">-</div>;
        }
      },
    },
    {
      accessorKey: "lastRunStatus",
      header: () => (
        <div className="text-center">{translations.status}</div>
      ),
      size: 120,
      minSize: 100,
      maxSize: 150,
      cell: ({ row }) => {
        const status = row.original.lastRunStatus;
        if (!status) {
          return <div className="text-center text-muted-foreground">-</div>;
        }
        const { icon: Icon, className } = getStatusBadge(status);
        return (
          <div className="flex justify-center">
            <Badge variant="outline" className={`flex items-center gap-1 w-fit ${className}`}>
              <Icon className="h-3 w-3" />
              {status}
            </Badge>
          </div>
        );
      },
    },
    {
      id: "actions",
      header: () => (
        <div className="text-center">{translations.actions}</div>
      ),
      size: 180,
      minSize: 180,
      maxSize: 180,
      cell: () => null, // Will be replaced in scheduler-table-body.tsx
    },
  ];
}
