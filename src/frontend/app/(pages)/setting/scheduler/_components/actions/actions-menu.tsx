"use client";

import { Button } from "@/components/ui/button";
import {
  Play,
  Eye,
  Edit,
  Trash2,
  Power,
  PowerOff,
  Loader2,
} from "lucide-react";
import { useState } from "react";
import { ViewJobSheet } from "../modal/view-job-sheet";
import { EditJobSheet } from "../modal/edit-job-sheet";
import {
  useSchedulerActions,
  useSchedulerUIState,
} from "../../context/scheduler-actions-context";
import { toast } from "sonner";
import type { ScheduledJob } from "@/types/scheduler";
import { useLanguage, translate } from "@/hooks/use-language";
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
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";

interface JobActionsProps {
  job: ScheduledJob;
  onUpdate: () => void;
  onJobUpdated?: (updatedJob: ScheduledJob) => void;
  disabled?: boolean;
}

export function JobActions({
  job,
  onUpdate,
  onJobUpdated,
  disabled = false,
}: JobActionsProps) {
  const { t, language } = useLanguage();
  const { onTriggerJob, onDeleteJob, onToggleJobEnabled } =
    useSchedulerActions();

  // Use context state for modals to pause polling when they're open
  const {
    selectedJob,
    setSelectedJob,
    isEditModalOpen,
    setIsEditModalOpen,
    isViewModalOpen,
    setIsViewModalOpen,
    isConfirmDialogOpen,
    setIsConfirmDialogOpen,
  } = useSchedulerUIState();

  const [isDeleting, setIsDeleting] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleViewJob = () => {
    setSelectedJob(job);
    setIsViewModalOpen(true);
  };

  const handleEditJob = () => {
    setSelectedJob(job);
    setIsEditModalOpen(true);
  };

  // Helper to get job display name
  const getJobDisplayName = (job: ScheduledJob, language: string) => {
    if (language === "ar") {
      return job.nameAr || job.taskFunction?.nameAr || job.jobKey;
    }
    return job.nameEn || job.taskFunction?.nameEn || job.jobKey;
  };

  const [isTriggerLoading, setIsTriggerLoading] = useState(false);

  const handleTriggerJob = () => {
    setSelectedJob(job); // Set the selected job so only this dialog renders
    setIsConfirmDialogOpen(true);
  };

  const handleConfirmTrigger = async () => {
    setIsTriggerLoading(true);
    try {
      const result = await onTriggerJob(job.id);
      if (result.success) {
        toast.success(result.message);
        // Update job if returned
        if (result.data && onJobUpdated) {
          onJobUpdated(result.data);
        }
        setIsConfirmDialogOpen(false); // Close on success
        setSelectedJob(null); // Clear selected job
      } else {
        toast.error(result.error || "Failed to trigger job");
        // Keep dialog open on error so user can see the error
      }
    } catch (error) {
      console.error("Failed to trigger job:", error);
      toast.error("Failed to trigger job");
    } finally {
      setIsTriggerLoading(false);
    }
  };

  const handleToggleEnabled = async () => {
    setIsToggling(true);
    try {
      const newEnabled = !job.isEnabled;
      const result = await onToggleJobEnabled(job.id, newEnabled);
      if (result.success) {
        toast.success(result.message);
        // Update parent state via callback
        if (onJobUpdated) {
          onJobUpdated({ ...job, isEnabled: newEnabled });
        } else {
          onUpdate();
        }
      } else {
        toast.error(
          result.error ||
            translate(t, "scheduler.toast.statusError") ||
            "Failed to update job status"
        );
      }
    } finally {
      setIsToggling(false);
    }
  };

  const handleDeleteJob = async () => {
    setIsDeleting(true);
    try {
      const result = await onDeleteJob(job.id);
      if (result.success) {
        toast.success(result.message);
        setShowDeleteDialog(false);
      } else {
        toast.error(result.error || "Failed to delete job");
      }
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <div className="flex items-center justify-center gap-1">
        {/* View */}
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={(e) => {
            e.stopPropagation();
            handleViewJob();
          }}
          disabled={disabled}
          title={translate(t, "scheduler.actions.view") || "View"}
        >
          <Eye className="h-4 w-4 text-blue-600" />
        </Button>

        {/* Run Now */}
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={(e) => {
            e.stopPropagation();
            handleTriggerJob();
          }}
          disabled={
            disabled ||
            !job.isEnabled ||
            job.currentExecutionStatus === "pending" ||
            job.currentExecutionStatus === "running"
          }
          title={
            job.currentExecutionStatus === "pending" ||
            job.currentExecutionStatus === "running"
              ? translate(t, "scheduler.actions.running") || "Running..."
              : translate(t, "scheduler.actions.runNow") || "Run Now"
          }
        >
          {job.currentExecutionStatus === "pending" ||
          job.currentExecutionStatus === "running" ? (
            <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
          ) : (
            <Play className="h-4 w-4 text-green-600" />
          )}
        </Button>

        {/* Edit */}
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={(e) => {
            e.stopPropagation();
            handleEditJob();
          }}
          disabled={disabled}
          title={translate(t, "scheduler.actions.edit") || "Edit"}
        >
          <Edit className="h-4 w-4 text-amber-600" />
        </Button>

        {/* Enable/Disable - Only for non-primary jobs */}
        {!job.isPrimary && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={(e) => {
              e.stopPropagation();
              handleToggleEnabled();
            }}
            disabled={disabled || isToggling}
            title={
              job.isEnabled
                ? translate(t, "scheduler.actions.disable") || "Disable"
                : translate(t, "scheduler.actions.enable") || "Enable"
            }
          >
            {isToggling ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : job.isEnabled ? (
              <PowerOff className="h-4 w-4 text-orange-500" />
            ) : (
              <Power className="h-4 w-4 text-green-600" />
            )}
          </Button>
        )}

        {/* Delete - Only for non-primary jobs */}
        {!job.isPrimary && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={(e) => {
              e.stopPropagation();
              setShowDeleteDialog(true);
            }}
            disabled={disabled}
            title={translate(t, "scheduler.actions.delete") || "Delete"}
          >
            <Trash2 className="h-4 w-4 text-red-600" />
          </Button>
        )}
      </div>

      {/* Sheets */}
      {isViewModalOpen && selectedJob && (
        <ViewJobSheet
          open={isViewModalOpen}
          onOpenChange={(open) => {
            if (!open) {
              setIsViewModalOpen(false);
              setSelectedJob(null);
            }
          }}
          job={selectedJob}
          onJobUpdated={(updatedJob) => {
            // Update selected job in context
            setSelectedJob(updatedJob);
            // Propagate to parent for SWR cache update
            if (onJobUpdated) {
              onJobUpdated(updatedJob);
            }
          }}
        />
      )}

      {isEditModalOpen && selectedJob && (
        <EditJobSheet
          open={isEditModalOpen}
          onOpenChange={(open) => {
            if (!open) {
              setIsEditModalOpen(false);
              setSelectedJob(null);
            }
          }}
          job={selectedJob}
          onSuccess={() => {
            onUpdate();
            setIsEditModalOpen(false);
            setSelectedJob(null);
          }}
          onJobUpdated={(updatedJob) => {
            // Update selected job in context
            setSelectedJob(updatedJob);
            // Propagate to parent for SWR cache update
            if (onJobUpdated) {
              onJobUpdated(updatedJob);
            } else {
              onUpdate();
            }
          }}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {translate(t, "scheduler.confirmations.deleteTitle") ||
                "Delete Job"}
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
              {isDeleting
                ? translate(t, "common.deleting") || "Deleting..."
                : translate(t, "common.delete") || "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Trigger Confirmation Dialog - Only render if this job is selected */}
      {isConfirmDialogOpen && selectedJob?.id === job.id && (
        <ConfirmationDialog
          open={true}
          onOpenChange={(open) => {
            setIsConfirmDialogOpen(open);
            if (!open) {
              setSelectedJob(null);
            }
          }}
          onConfirm={handleConfirmTrigger}
          isLoading={isTriggerLoading}
          title={
            translate(t, "scheduler.confirmations.triggerTitle") ||
            "Run Task Now"
          }
          description={
            translate(t, "scheduler.confirmations.triggerMessage")?.replace(
              "{jobName}",
              getJobDisplayName(job, language)
            ) ||
            `Are you sure you want to run "${getJobDisplayName(
              job,
              language
            )}" now? This will execute the task immediately.`
          }
          confirmText={translate(t, "confirmDialog.confirm") || "Confirm"}
          cancelText={translate(t, "confirmDialog.cancel") || "Cancel"}
        />
      )}
    </>
  );
}
