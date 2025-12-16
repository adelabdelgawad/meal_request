"use client";

import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { format } from "date-fns";
import { ar, enUS } from "date-fns/locale";
import type { ScheduledJob } from "@/types/scheduler";
import { useLanguage, translate } from "@/hooks/use-language";
import { useSchedulerActions } from "../../context/scheduler-actions-context";
import { toast } from "sonner";
import {
  Clock,
  Calendar,
  CheckCircle,
  XCircle,
  Settings,
  Timer,
  Code,
  Shield,
  Eye,
  X,
  Play,
  Power,
  PowerOff,
  Trash2,
  Loader2,
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface ViewJobSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  job: ScheduledJob;
  onJobUpdated?: (updatedJob: ScheduledJob) => void;
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

  return parts.length > 0 ? parts.join(" ") : "";
}

export function ViewJobSheet({
  open,
  onOpenChange,
  job: initialJob,
  onJobUpdated,
}: ViewJobSheetProps) {
  const { t, language, dir } = useLanguage();
  const locale = language === "ar" ? ar : enUS;
  const isRTL = dir === "rtl";

  const { onToggleJobEnabled, onTriggerJob, onDeleteJob } = useSchedulerActions();

  // Local state for job to reflect updates immediately
  const [job, setJob] = useState<ScheduledJob>(initialJob);
  const [isToggling, setIsToggling] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Update local state when initial job changes
  if (initialJob.id !== job.id) {
    setJob(initialJob);
  }

  const name = language === "ar" ? job.nameAr : job.nameEn;
  const description = language === "ar" ? job.descriptionAr : job.descriptionEn;

  const handleClose = () => {
    onOpenChange(false);
  };

  const handleToggleEnabled = async () => {
    setIsToggling(true);
    try {
      const result = await onToggleJobEnabled(job.id, !job.isEnabled);
      if (result.success) {
        const updatedJob = { ...job, isEnabled: !job.isEnabled };
        setJob(updatedJob);
        onJobUpdated?.(updatedJob);
        toast.success(result.message);
      } else {
        toast.error(result.error || translate(t, "scheduler.toast.statusError") || "Failed to update job status");
      }
    } finally {
      setIsToggling(false);
    }
  };

  const handleTriggerJob = async () => {
    setIsTriggering(true);
    try {
      const result = await onTriggerJob(job.id);
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.error || "Failed to trigger job");
      }
    } finally {
      setIsTriggering(false);
    }
  };

  const handleDeleteJob = async () => {
    setIsDeleting(true);
    try {
      const result = await onDeleteJob(job.id);
      if (result.success) {
        toast.success(result.message);
        setShowDeleteDialog(false);
        onOpenChange(false);
      } else {
        toast.error(result.error || "Failed to delete job");
      }
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent
          side={isRTL ? "left" : "right"}
          className="w-full sm:max-w-lg flex flex-col p-0"
        >
          {/* Header */}
          <SheetHeader className="px-4 pt-4 pb-2 shrink-0 border-b">
            <SheetTitle className={`flex items-center gap-2 text-base ${isRTL ? "flex-row-reverse" : ""}`}>
              <div className="p-1 bg-primary/10">
                <Eye className="h-3.5 w-3.5 text-primary" />
              </div>
              {translate(t, "scheduler.actions.view") || "View Job"}
              {job.isPrimary && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                  <Shield className="h-2.5 w-2.5 me-0.5" />
                  {translate(t, "scheduler.primary") || "Primary"}
                </Badge>
              )}
            </SheetTitle>
            <SheetDescription className="text-xs truncate">
              {name}
            </SheetDescription>
          </SheetHeader>

          {/* Actions Bar */}
          <div className="px-4 py-2 border-b bg-muted/30 flex items-center gap-2 shrink-0">
            {/* Run Now */}
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={handleTriggerJob}
              disabled={isTriggering || !job.isEnabled}
            >
              {isTriggering ? (
                <Loader2 className="h-3 w-3 me-1 animate-spin" />
              ) : (
                <Play className="h-3 w-3 me-1 text-green-600" />
              )}
              {translate(t, "scheduler.actions.runNow") || "Run Now"}
            </Button>

            {/* Enable/Disable */}
            {!job.isPrimary && (
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                onClick={handleToggleEnabled}
                disabled={isToggling}
              >
                {isToggling ? (
                  <Loader2 className="h-3 w-3 me-1 animate-spin" />
                ) : job.isEnabled ? (
                  <PowerOff className="h-3 w-3 me-1 text-orange-500" />
                ) : (
                  <Power className="h-3 w-3 me-1 text-green-600" />
                )}
                {job.isEnabled
                  ? translate(t, "scheduler.actions.disable") || "Disable"
                  : translate(t, "scheduler.actions.enable") || "Enable"}
              </Button>
            )}

            {/* Delete */}
            {!job.isPrimary && (
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs text-red-600 hover:text-red-700 hover:bg-red-50 ms-auto"
                onClick={() => setShowDeleteDialog(true)}
                disabled={isDeleting}
              >
                <Trash2 className="h-3 w-3 me-1" />
                {translate(t, "scheduler.actions.delete") || "Delete"}
              </Button>
            )}
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto px-4 py-3">
            <div className="space-y-3">
              {/* Status Section */}
              <section>
                <h3 className="text-xs font-semibold flex items-center gap-1.5 mb-2 text-muted-foreground uppercase tracking-wide">
                  <Timer className="h-3 w-3" />
                  {translate(t, "scheduler.sections.status") || "Status"}
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2 bg-muted/50 border">
                    <Label className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.enabled") || "Status"}
                    </Label>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {job.isEnabled ? (
                        <>
                          <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                          <span className="text-xs font-medium text-green-600">
                            {translate(t, "scheduler.status.enabled") || "Enabled"}
                          </span>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-3.5 w-3.5 text-gray-400" />
                          <span className="text-xs text-gray-500">
                            {translate(t, "scheduler.status.disabled") || "Disabled"}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="p-2 bg-muted/50 border">
                    <Label className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.lastStatus") || "Last Run"}
                    </Label>
                    <div className="mt-0.5">
                      {job.lastRunStatus ? (
                        <Badge
                          variant="outline"
                          className={`text-[10px] px-1.5 py-0 ${
                            job.lastRunStatus === "completed"
                              ? "bg-green-50 text-green-700 border-green-200"
                              : job.lastRunStatus === "failed"
                              ? "bg-red-50 text-red-700 border-red-200"
                              : ""
                          }`}
                        >
                          {job.lastRunStatus}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          {translate(t, "scheduler.neverRun") || "Never"}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </section>

              <Separator />

              {/* Schedule Section */}
              <section>
                <h3 className="text-xs font-semibold flex items-center gap-1.5 mb-2 text-muted-foreground uppercase tracking-wide">
                  {job.jobType === "cron" ? (
                    <Calendar className="h-3 w-3" />
                  ) : (
                    <Clock className="h-3 w-3" />
                  )}
                  {translate(t, "scheduler.sections.schedule") || "Schedule"}
                </h3>
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center p-2 bg-muted/50 border">
                    <span className="text-xs text-muted-foreground">
                      {translate(t, "scheduler.fields.type") || "Type"}
                    </span>
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                      {job.jobType === "cron" ? (
                        <Calendar className="h-2.5 w-2.5 me-1" />
                      ) : (
                        <Clock className="h-2.5 w-2.5 me-1" />
                      )}
                      {job.jobType}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-muted/50 border">
                    <span className="text-xs text-muted-foreground">
                      {translate(t, "scheduler.fields.schedule") || "Schedule"}
                    </span>
                    <span className="font-mono text-xs">
                      {formatSchedule(job) || translate(t, "scheduler.schedule.notConfigured") || "Not configured"}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-muted/50 border">
                    <span className="text-xs text-muted-foreground">
                      {translate(t, "scheduler.fields.nextRun") || "Next Run"}
                    </span>
                    <span className="text-xs">
                      {job.nextRunTime
                        ? format(new Date(job.nextRunTime), "MMM d, HH:mm", { locale })
                        : "-"}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-muted/50 border">
                    <span className="text-xs text-muted-foreground">
                      {translate(t, "scheduler.fields.lastRun") || "Last Run"}
                    </span>
                    <span className="text-xs">
                      {job.lastRunTime
                        ? format(new Date(job.lastRunTime), "MMM d, HH:mm", { locale })
                        : translate(t, "scheduler.neverRun") || "Never"}
                    </span>
                  </div>
                </div>
              </section>

              <Separator />

              {/* Configuration Section */}
              <section>
                <h3 className="text-xs font-semibold flex items-center gap-1.5 mb-2 text-muted-foreground uppercase tracking-wide">
                  <Settings className="h-3 w-3" />
                  {translate(t, "scheduler.sections.configuration") || "Configuration"}
                </h3>
                <div className="grid grid-cols-2 gap-1.5">
                  <div className="p-2 bg-muted/50 border">
                    <Label className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.priority") || "Priority"}
                    </Label>
                    <div className="text-xs font-medium mt-0.5">{job.priority}</div>
                  </div>
                  <div className="p-2 bg-muted/50 border">
                    <Label className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.maxInstances") || "Max Inst."}
                    </Label>
                    <div className="text-xs font-medium mt-0.5">{job.maxInstances}</div>
                  </div>
                  <div className="p-2 bg-muted/50 border">
                    <Label className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.misfireGrace") || "Misfire (s)"}
                    </Label>
                    <div className="text-xs font-medium mt-0.5">{job.misfireGraceTime}</div>
                  </div>
                  <div className="p-2 bg-muted/50 border">
                    <Label className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.coalesce") || "Coalesce"}
                    </Label>
                    <div className="text-xs font-medium mt-0.5">
                      {job.coalesce
                        ? translate(t, "common.yes") || "Yes"
                        : translate(t, "common.no") || "No"}
                    </div>
                  </div>
                </div>
              </section>

              <Separator />

              {/* Technical Details Section */}
              <section>
                <h3 className="text-xs font-semibold flex items-center gap-1.5 mb-2 text-muted-foreground uppercase tracking-wide">
                  <Code className="h-3 w-3" />
                  {translate(t, "scheduler.sections.technical") || "Technical"}
                </h3>
                <div className="space-y-1.5">
                  <div className="p-2 bg-muted/50 border">
                    <Label className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.jobKey") || "Job Key"}
                    </Label>
                    <div className="font-mono text-xs mt-0.5 truncate">{job.jobKey}</div>
                  </div>
                  <div className="p-2 bg-muted/50 border">
                    <Label className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.function") || "Function"}
                    </Label>
                    <div className="font-mono text-[10px] mt-0.5 break-all text-muted-foreground">
                      {job.jobFunction}
                    </div>
                  </div>
                  {description && (
                    <div className="p-2 bg-muted/50 border">
                      <Label className="text-[10px] text-muted-foreground uppercase">
                        Description
                      </Label>
                      <div className="text-xs mt-0.5 text-muted-foreground">
                        {description}
                      </div>
                    </div>
                  )}
                </div>
              </section>

              {/* Timestamps */}
              <div className="text-[10px] text-muted-foreground pt-2 space-y-0.5">
                <div>
                  Created: {format(new Date(job.createdAt), "PPp", { locale })}
                </div>
                <div>
                  Updated: {format(new Date(job.updatedAt), "PPp", { locale })}
                </div>
                <div className="font-mono text-[9px] opacity-60">ID: {job.id}</div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <SheetFooter className="px-4 py-2 border-t shrink-0 bg-background">
            <Button
              variant="outline"
              size="sm"
              onClick={handleClose}
              className="w-full h-8"
            >
              <X className="h-3.5 w-3.5 me-1.5" />
              {translate(t, "common.close") || "Close"}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {translate(t, "scheduler.confirmations.deleteTitle") || "Delete Scheduled Job"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {translate(t, "scheduler.confirmations.deleteMessage") ||
                "Are you sure you want to delete this scheduled job? This action cannot be undone."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {translate(t, "common.cancel") || "Cancel"}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteJob}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 me-2 animate-spin" />
                  {translate(t, "common.deleting") || "Deleting..."}
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 me-2" />
                  {translate(t, "common.delete") || "Delete"}
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
