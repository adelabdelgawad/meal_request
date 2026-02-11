"use client";

import React from "react";
import { Button } from "@/components/data-table";
import { toast } from "sonner";
import { CreateJobSheet } from "../modal/create-job-sheet";
import { CalendarPlus } from "lucide-react";
import type { ScheduledJobCreate } from "@/types/scheduler";
import { useLanguage, translate } from "@/hooks/use-language";
import { useSchedulerActions, useSchedulerUIState } from "../../context/scheduler-actions-context";

interface AddScheduleButtonProps {
  onAdd: () => void;
}

export const AddScheduleButton: React.FC<AddScheduleButtonProps> = ({ onAdd }) => {
  const { t } = useLanguage();
  const { onCreateJob } = useSchedulerActions();
  const { isCreateModalOpen, setIsCreateModalOpen } = useSchedulerUIState();

  const handleCreate = async (data: ScheduledJobCreate) => {
    const result = await onCreateJob(data);
    if (result.success) {
      toast.success(result.message || translate(t, "scheduler.toast.createSuccess") || "Job created successfully");
      onAdd();
      setIsCreateModalOpen(false);
      return { success: true };
    } else {
      toast.error(result.error || translate(t, "scheduler.toast.createError") || "Failed to create job");
      return { success: false, error: result.error };
    }
  };

  return (
    <>
      <Button
        onClick={() => setIsCreateModalOpen(true)}
        variant="primary"
        size="default"
        icon={<CalendarPlus className="w-4 h-4" />}
        tooltip={translate(t, "scheduler.create.tooltip") || "Add a new scheduled job"}
      >
        {translate(t, "scheduler.create.button") || "Add Schedule"}
      </Button>

      <CreateJobSheet
        open={isCreateModalOpen}
        onOpenChange={setIsCreateModalOpen}
        onCreateJob={handleCreate}
        onSuccess={onAdd}
      />
    </>
  );
};
