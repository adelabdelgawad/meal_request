"use client";

import { Timer, Activity, Server, CheckCircle, XCircle, Clock, AlertTriangle, Loader2 } from "lucide-react";
import { StatusPanel as BaseStatusPanel } from "@/components/data-table";
import React from "react";
import type { SchedulerInstance, JobExecution } from "@/types/scheduler";
import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "date-fns";
import { useLanguage, translate } from "@/hooks/use-language";
import { ar, enUS } from "date-fns/locale";

type StatusPanelProps = {
  totalJobs: number;
  enabledCount: number;
  disabledCount: number;
  isRunning: boolean;
  activeInstances: SchedulerInstance[];
  recentExecutions: JobExecution[];
};

/**
 * Get status icon, colors, and badge variant for execution status
 */
function getStatusDisplay(status: string) {
  switch (status) {
    case "completed":
      return {
        icon: CheckCircle,
        color: "text-green-600 dark:text-green-400",
        bg: "bg-green-50 dark:bg-green-950/30",
        border: "border-green-200 dark:border-green-800",
        badgeClass: "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300",
      };
    case "running":
      return {
        icon: Loader2,
        color: "text-blue-600 dark:text-blue-400",
        bg: "bg-blue-50 dark:bg-blue-950/30",
        border: "border-blue-200 dark:border-blue-800",
        badgeClass: "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300",
        animate: true,
      };
    case "failed":
      return {
        icon: XCircle,
        color: "text-red-600 dark:text-red-400",
        bg: "bg-red-50 dark:bg-red-950/30",
        border: "border-red-200 dark:border-red-800",
        badgeClass: "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
      };
    case "queued":
      return {
        icon: Clock,
        color: "text-amber-600 dark:text-amber-400",
        bg: "bg-amber-50 dark:bg-amber-950/30",
        border: "border-amber-200 dark:border-amber-800",
        badgeClass: "bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300",
      };
    default:
      return {
        icon: AlertTriangle,
        color: "text-gray-600 dark:text-gray-400",
        bg: "bg-gray-50 dark:bg-gray-900/30",
        border: "border-gray-200 dark:border-gray-700",
        badgeClass: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
      };
  }
}

export const StatusPanel: React.FC<StatusPanelProps> = ({
  totalJobs,
  enabledCount,
  disabledCount,
  isRunning,
  activeInstances,
  recentExecutions,
}) => {
  const { t, language } = useLanguage();
  const locale = language === "ar" ? ar : enUS;

  return (
    <BaseStatusPanel
      totalCount={totalJobs}
      activeCount={enabledCount}
      inactiveCount={disabledCount}
      entityLabel={translate(t, "statusPanel.job") || "Job"}
      icon={Timer}
      queryParam="is_enabled"
      extraContent={
        <div className="space-y-4 mt-4">
          {/* Scheduler Status */}
          <div className="p-3 bg-muted/50 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium flex items-center gap-2">
                <Activity className="h-4 w-4" />
                {translate(t, "scheduler.schedulerStatus") || "Scheduler Status"}
              </span>
              <Badge
                variant={isRunning ? "default" : "secondary"}
                className={isRunning ? "bg-green-600" : "bg-gray-500"}
              >
                {isRunning
                  ? translate(t, "scheduler.status.running") || "Running"
                  : translate(t, "scheduler.status.stopped") || "Stopped"}
              </Badge>
            </div>
          </div>

          {/* Active Instances */}
          {activeInstances.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <Server className="h-4 w-4" />
                {translate(t, "scheduler.activeInstances") || "Active Instances"}
              </h4>
              <div className="space-y-1">
                {activeInstances.map((instance) => (
                  <div
                    key={instance.id}
                    className="flex items-center justify-between p-2 bg-muted/30 rounded text-xs"
                  >
                    <div className="flex flex-col">
                      <span className="font-medium">{instance.instanceName}</span>
                      <span className="text-muted-foreground">
                        {instance.hostName} ({instance.mode})
                      </span>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {instance.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent Executions */}
          {recentExecutions.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">
                {translate(t, "scheduler.recentExecutions") || "Recent Executions"}
              </h4>
              <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
                {recentExecutions.slice(0, 5).map((execution) => {
                  const statusDisplay = getStatusDisplay(execution.status);
                  const StatusIcon = statusDisplay.icon;
                  const isAnimated = 'animate' in statusDisplay && statusDisplay.animate;
                  return (
                    <div
                      key={execution.id}
                      className={`flex items-center justify-between p-2 border text-xs ${statusDisplay.bg} ${statusDisplay.border}`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <StatusIcon className={`h-3.5 w-3.5 shrink-0 ${statusDisplay.color} ${isAnimated ? 'animate-spin' : ''}`} />
                        <span className="font-mono truncate">
                          {execution.executionId?.slice(0, 8)}
                        </span>
                      </div>
                      <div className="flex flex-col items-end gap-0.5 shrink-0">
                        <Badge variant="outline" className={`text-[10px] px-1.5 py-0 h-4 border-0 ${statusDisplay.badgeClass}`}>
                          {execution.status}
                        </Badge>
                        {execution.startedAt && (
                          <span className="text-[10px] text-muted-foreground">
                            {formatDistanceToNow(new Date(execution.startedAt), {
                              addSuffix: true,
                              locale,
                            })}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      }
    />
  );
};
