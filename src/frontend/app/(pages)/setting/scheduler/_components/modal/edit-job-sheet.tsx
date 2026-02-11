"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/components/ui/custom-toast";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import type { ScheduledJob, ScheduledJobUpdate, SchedulerJobType } from "@/types/scheduler";
import { useSchedulerActions } from "../../context/scheduler-actions-context";
import { useLanguage, translate } from "@/hooks/use-language";
import { getJobTypes } from "@/lib/actions/scheduler.actions";
import {
  Timer,
  Save,
  Loader2,
  Edit,
  Clock,
  Calendar,
  Settings,
} from "lucide-react";

interface EditJobSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  job: ScheduledJob;
  onSuccess: () => void;
  onJobUpdated?: (updatedJob: ScheduledJob) => void;
}

// Comparison function for job data
function areJobsEqual(a: ScheduledJobUpdate, b: ScheduledJobUpdate): boolean {
  return (
    a.nameEn === b.nameEn &&
    a.nameAr === b.nameAr &&
    a.descriptionEn === b.descriptionEn &&
    a.descriptionAr === b.descriptionAr &&
    a.jobTypeId === b.jobTypeId &&
    a.intervalSeconds === b.intervalSeconds &&
    a.intervalMinutes === b.intervalMinutes &&
    a.intervalHours === b.intervalHours &&
    a.intervalDays === b.intervalDays &&
    a.cronExpression === b.cronExpression &&
    a.priority === b.priority &&
    a.maxInstances === b.maxInstances &&
    a.misfireGraceTime === b.misfireGraceTime &&
    a.coalesce === b.coalesce &&
    a.isEnabled === b.isEnabled
  );
}

export function EditJobSheet({
  open,
  onOpenChange,
  job,
  onSuccess,
  onJobUpdated,
}: EditJobSheetProps) {
  const { t, language, dir } = useLanguage();
  const isRTL = dir === "rtl";
  const { onUpdateJob } = useSchedulerActions();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [jobTypes, setJobTypes] = useState<SchedulerJobType[]>([]);
  const [isLoadingLookups, setIsLoadingLookups] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [formData, setFormData] = useState<ScheduledJobUpdate>({
    nameEn: job.nameEn ?? undefined,
    nameAr: job.nameAr ?? undefined,
    descriptionEn: job.descriptionEn ?? "",
    descriptionAr: job.descriptionAr ?? "",
    jobTypeId: job.jobTypeId,
    intervalSeconds: job.intervalSeconds ?? undefined,
    intervalMinutes: job.intervalMinutes ?? undefined,
    intervalHours: job.intervalHours ?? undefined,
    intervalDays: job.intervalDays ?? undefined,
    cronExpression: job.cronExpression ?? "",
    priority: job.priority,
    maxInstances: job.maxInstances,
    misfireGraceTime: job.misfireGraceTime,
    coalesce: job.coalesce,
    isEnabled: job.isEnabled,
  });

  // Store initial values in a ref to avoid re-renders
  const initialValues = useRef<ScheduledJobUpdate>({
    nameEn: job.nameEn ?? undefined,
    nameAr: job.nameAr ?? undefined,
    descriptionEn: job.descriptionEn ?? "",
    descriptionAr: job.descriptionAr ?? "",
    jobTypeId: job.jobTypeId,
    intervalSeconds: job.intervalSeconds ?? undefined,
    intervalMinutes: job.intervalMinutes ?? undefined,
    intervalHours: job.intervalHours ?? undefined,
    intervalDays: job.intervalDays ?? undefined,
    cronExpression: job.cronExpression ?? "",
    priority: job.priority,
    maxInstances: job.maxInstances,
    misfireGraceTime: job.misfireGraceTime,
    coalesce: job.coalesce,
    isEnabled: job.isEnabled,
  });

  const name = language === "ar" ? job.nameAr : job.nameEn;

  // Get current job type code
  const currentJobType = jobTypes.find((jt) => jt.id === formData.jobTypeId);
  const isIntervalType = currentJobType?.code === "interval";

  // Load job types when sheet opens
  const loadJobTypes = useCallback(async () => {
    setIsLoadingLookups(true);
    try {
      const data = await getJobTypes();
      setJobTypes(data);
    } catch (error) {
      console.error("Failed to load job types:", error);
    } finally {
      setIsLoadingLookups(false);
    }
  }, []);

  const closeSheet = () => {
    setIsMounted(false);
    setIsDirty(false);
    onOpenChange(false);
  };

  // Perform save action
  const performSave = async () => {
    setIsSubmitting(true);

    try {
      const dataToSubmit: ScheduledJobUpdate = { ...formData };

      // Clear irrelevant fields based on job type
      if (!isIntervalType) {
        // Cron type - clear interval fields
        dataToSubmit.intervalSeconds = undefined;
        dataToSubmit.intervalMinutes = undefined;
        dataToSubmit.intervalHours = undefined;
        dataToSubmit.intervalDays = undefined;
      } else {
        // Interval type - clear cron expression
        dataToSubmit.cronExpression = undefined;
      }

      const result = await onUpdateJob(job.id, dataToSubmit);

      if (result.success) {
        toast.success(result.message || translate(t, "scheduler.toast.updateSuccess") || "Job updated successfully");
        setIsDirty(false);
        onOpenChange(false);

        // Use the backend response directly
        if (onJobUpdated && result.data) {
          onJobUpdated(result.data);
        } else {
          onSuccess();
        }
      } else {
        toast.error(result.error || translate(t, "scheduler.toast.updateError") || "Failed to update job");
        throw new Error(result.error); // Prevent dialog from closing
      }
    } catch (error) {
      console.error("Failed to update job:", error);
      toast.error(translate(t, "scheduler.toast.updateError") || "Failed to update job");
      throw error; // Re-throw to prevent dialog from closing
    } finally {
      setIsSubmitting(false);
    }
  };

  // Confirmation dialog for closing with unsaved changes
  const {
    isOpen: showCloseConfirmDialog,
    isLoading: closeConfirmLoading,
    open: openCloseDialog,
    close: closeCloseDialog,
    confirm: handleCloseConfirm,
    confirmLabel: closeConfirmLabel,
    cancelLabel: closeCancelLabel,
  } = useConfirmationDialog(closeSheet);

  // Confirmation dialog for saving changes
  const {
    isOpen: showSaveConfirmDialog,
    isLoading: saveConfirmLoading,
    open: openSaveDialog,
    close: closeSaveDialog,
    confirm: handleSaveConfirm,
    confirmLabel: saveConfirmLabel,
    cancelLabel: saveCancelLabel,
  } = useConfirmationDialog(performSave);

  // Initialize form when sheet opens
  useEffect(() => {
    if (open && job) {
      setIsMounted(true);

      // Transform job data to form state
      const initialData: ScheduledJobUpdate = {
        nameEn: job.nameEn ?? undefined,
        nameAr: job.nameAr ?? undefined,
        descriptionEn: job.descriptionEn ?? "",
        descriptionAr: job.descriptionAr ?? "",
        jobTypeId: job.jobTypeId,
        intervalSeconds: job.intervalSeconds ?? undefined,
        intervalMinutes: job.intervalMinutes ?? undefined,
        intervalHours: job.intervalHours ?? undefined,
        intervalDays: job.intervalDays ?? undefined,
        cronExpression: job.cronExpression ?? "",
        priority: job.priority,
        maxInstances: job.maxInstances,
        misfireGraceTime: job.misfireGraceTime,
        coalesce: job.coalesce,
        isEnabled: job.isEnabled,
      };

      setFormData(initialData);
      initialValues.current = initialData;
      setIsDirty(false);
      loadJobTypes();
    }
  }, [open, job, loadJobTypes]);

  // Track changes after mount
  useEffect(() => {
    if (!isMounted) {
      return;
    }
    const dirty = !areJobsEqual(formData, initialValues.current);
    setIsDirty(dirty);
  }, [formData, isMounted]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    openSaveDialog();
  };

  const handleClose = () => {
    if (isDirty) {
      openCloseDialog();
      return;
    }
    closeSheet();
  };

  const updateFormData = (field: keyof ScheduledJobUpdate, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  if (!isMounted) {
    return null;
  }

  return (
    <>
      <Sheet open={open} onOpenChange={handleClose}>
      <SheetContent
        side={isRTL ? "left" : "right"}
        className="w-full sm:max-w-lg flex flex-col p-0"
      >
        {/* Header */}
        <SheetHeader className="px-4 pt-4 pb-2 shrink-0 border-b">
          <SheetTitle className={`flex items-center justify-between text-base ${isRTL ? "flex-row-reverse" : ""}`}>
            <div className={`flex items-center gap-2 ${isRTL ? "flex-row-reverse" : ""}`}>
              <div className="p-1 bg-primary/10">
                <Edit className="h-3.5 w-3.5 text-primary" />
              </div>
              {translate(t, "scheduler.edit.title") || "Edit Job"}
            </div>
            {isDirty && (
              <span className="text-sm text-orange-600 font-normal">
                • {translate(t, "scheduler.unsavedChanges") || "Unsaved changes"}
              </span>
            )}
          </SheetTitle>
          <SheetDescription className="text-xs truncate">
            {name}
          </SheetDescription>
        </SheetHeader>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          <form id="edit-job-form" onSubmit={handleSubmit} className="space-y-3">
            {/* Name & Description Section */}
            <section>
              <h3 className="text-xs font-semibold flex items-center gap-1.5 mb-2 text-muted-foreground uppercase tracking-wide">
                <Timer className="h-3 w-3" />
                {translate(t, "scheduler.edit.nameSection") || "Name & Description"}
              </h3>
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2 bg-muted/50 border space-y-1">
                    <Label htmlFor="nameEn" className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.nameEn") || "Name (EN)"}
                    </Label>
                    <Input
                      id="nameEn"
                      value={formData.nameEn}
                      onChange={(e) => updateFormData("nameEn", e.target.value)}
                      className="h-7 text-xs"
                      required
                    />
                  </div>
                  <div className="p-2 bg-muted/50 border space-y-1">
                    <Label htmlFor="nameAr" className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.nameAr") || "Name (AR)"}
                    </Label>
                    <Input
                      id="nameAr"
                      value={formData.nameAr}
                      onChange={(e) => updateFormData("nameAr", e.target.value)}
                      className="h-7 text-xs"
                      dir="rtl"
                      required
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2 bg-muted/50 border space-y-1">
                    <Label htmlFor="descriptionEn" className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.descriptionEn") || "Desc (EN)"}
                    </Label>
                    <Textarea
                      id="descriptionEn"
                      value={formData.descriptionEn}
                      onChange={(e) => updateFormData("descriptionEn", e.target.value)}
                      rows={2}
                      className="resize-none text-xs min-h-[50px]"
                    />
                  </div>
                  <div className="p-2 bg-muted/50 border space-y-1">
                    <Label htmlFor="descriptionAr" className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.descriptionAr") || "Desc (AR)"}
                    </Label>
                    <Textarea
                      id="descriptionAr"
                      value={formData.descriptionAr}
                      onChange={(e) => updateFormData("descriptionAr", e.target.value)}
                      dir="rtl"
                      rows={2}
                      className="resize-none text-xs min-h-[50px]"
                    />
                  </div>
                </div>
              </div>
            </section>

            <Separator />

            {/* Schedule Section */}
            <section>
              <h3 className="text-xs font-semibold flex items-center gap-1.5 mb-2 text-muted-foreground uppercase tracking-wide">
                {isIntervalType ? (
                  <Clock className="h-3 w-3" />
                ) : (
                  <Calendar className="h-3 w-3" />
                )}
                {translate(t, "scheduler.edit.scheduleSection") || "Schedule"}
              </h3>
              <div className="space-y-2">
                <div className="p-2 bg-muted/50 border space-y-1">
                  <Label htmlFor="jobTypeId" className="text-[10px] text-muted-foreground uppercase">
                    {translate(t, "scheduler.fields.type") || "Type"}
                  </Label>
                  <Select
                    value={formData.jobTypeId?.toString() || ""}
                    onValueChange={(value) =>
                      updateFormData("jobTypeId", parseInt(value, 10))
                    }
                    disabled={isLoadingLookups}
                  >
                    <SelectTrigger className="h-7 text-xs">
                      <SelectValue placeholder={
                        isLoadingLookups
                          ? translate(t, "common.loading") || "Loading..."
                          : translate(t, "scheduler.fields.selectJobType") || "Select job type"
                      } />
                    </SelectTrigger>
                    <SelectContent>
                      {jobTypes.map((jt) => (
                        <SelectItem key={jt.id} value={jt.id.toString()} className="text-xs">
                          <span className="flex items-center gap-1.5">
                            {jt.code === "interval" ? (
                              <Clock className="h-3 w-3" />
                            ) : (
                              <Calendar className="h-3 w-3" />
                            )}
                            {language === "ar" ? jt.nameAr : jt.nameEn}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {isIntervalType ? (
                  <div className="grid grid-cols-4 gap-1.5">
                    <div className="p-2 bg-muted/50 border space-y-1">
                      <Label htmlFor="intervalDays" className="text-[10px] text-muted-foreground uppercase">
                        {translate(t, "scheduler.fields.days") || "Days"}
                      </Label>
                      <Input
                        id="intervalDays"
                        type="number"
                        min="0"
                        value={formData.intervalDays || ""}
                        onChange={(e) =>
                          updateFormData("intervalDays", e.target.value ? parseInt(e.target.value) : undefined)
                        }
                        className="h-7 text-xs"
                      />
                    </div>
                    <div className="p-2 bg-muted/50 border space-y-1">
                      <Label htmlFor="intervalHours" className="text-[10px] text-muted-foreground uppercase">
                        {translate(t, "scheduler.fields.hours") || "Hrs"}
                      </Label>
                      <Input
                        id="intervalHours"
                        type="number"
                        min="0"
                        max="23"
                        value={formData.intervalHours || ""}
                        onChange={(e) =>
                          updateFormData("intervalHours", e.target.value ? parseInt(e.target.value) : undefined)
                        }
                        className="h-7 text-xs"
                      />
                    </div>
                    <div className="p-2 bg-muted/50 border space-y-1">
                      <Label htmlFor="intervalMinutes" className="text-[10px] text-muted-foreground uppercase">
                        {translate(t, "scheduler.fields.minutes") || "Min"}
                      </Label>
                      <Input
                        id="intervalMinutes"
                        type="number"
                        min="0"
                        max="59"
                        value={formData.intervalMinutes || ""}
                        onChange={(e) =>
                          updateFormData("intervalMinutes", e.target.value ? parseInt(e.target.value) : undefined)
                        }
                        className="h-7 text-xs"
                      />
                    </div>
                    <div className="p-2 bg-muted/50 border space-y-1">
                      <Label htmlFor="intervalSeconds" className="text-[10px] text-muted-foreground uppercase">
                        {translate(t, "scheduler.fields.seconds") || "Sec"}
                      </Label>
                      <Input
                        id="intervalSeconds"
                        type="number"
                        min="0"
                        max="59"
                        value={formData.intervalSeconds || ""}
                        onChange={(e) =>
                          updateFormData("intervalSeconds", e.target.value ? parseInt(e.target.value) : undefined)
                        }
                        className="h-7 text-xs"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="p-2 bg-muted/50 border space-y-1">
                    <Label htmlFor="cronExpression" className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.cronExpression") || "Cron Expression"}
                    </Label>
                    <Input
                      id="cronExpression"
                      value={formData.cronExpression}
                      onChange={(e) => updateFormData("cronExpression", e.target.value)}
                      placeholder="0 * * * *"
                      className="font-mono h-7 text-xs"
                    />
                    <p className="text-[10px] text-muted-foreground">
                      {translate(t, "scheduler.edit.cronHelp") || "minute hour day month weekday"}
                    </p>
                  </div>
                )}
              </div>
            </section>

            <Separator />

            {/* Configuration Section */}
            <section>
              <h3 className="text-xs font-semibold flex items-center gap-1.5 mb-2 text-muted-foreground uppercase tracking-wide">
                <Settings className="h-3 w-3" />
                {translate(t, "scheduler.edit.configSection") || "Configuration"}
              </h3>
              <div className="space-y-2">
                <div className="grid grid-cols-3 gap-1.5">
                  <div className="p-2 bg-muted/50 border space-y-1">
                    <Label htmlFor="priority" className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.priority") || "Priority"}
                    </Label>
                    <Input
                      id="priority"
                      type="number"
                      min="0"
                      max="100"
                      value={formData.priority}
                      onChange={(e) => updateFormData("priority", parseInt(e.target.value) || 0)}
                      className="h-7 text-xs"
                    />
                  </div>
                  <div className="p-2 bg-muted/50 border space-y-1">
                    <Label htmlFor="maxInstances" className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.maxInstances") || "Max Inst."}
                    </Label>
                    <Input
                      id="maxInstances"
                      type="number"
                      min="1"
                      value={formData.maxInstances}
                      onChange={(e) => updateFormData("maxInstances", parseInt(e.target.value) || 1)}
                      className="h-7 text-xs"
                    />
                  </div>
                  <div className="p-2 bg-muted/50 border space-y-1">
                    <Label htmlFor="misfireGraceTime" className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.misfireGrace") || "Misfire (s)"}
                    </Label>
                    <Input
                      id="misfireGraceTime"
                      type="number"
                      min="0"
                      value={formData.misfireGraceTime}
                      onChange={(e) => updateFormData("misfireGraceTime", parseInt(e.target.value) || 300)}
                      className="h-7 text-xs"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-1.5">
                  <div className="flex items-center justify-between p-2 bg-muted/50 border">
                    <Label htmlFor="coalesce" className="text-xs">
                      {translate(t, "scheduler.fields.coalesce") || "Coalesce"}
                    </Label>
                    <Switch
                      id="coalesce"
                      checked={formData.coalesce}
                      onCheckedChange={(checked) => updateFormData("coalesce", checked)}
                    />
                  </div>
                  <div className="flex items-center justify-between p-2 bg-primary/5 border border-primary/20">
                    <Label htmlFor="isEnabled" className="text-xs font-medium">
                      {translate(t, "scheduler.fields.enabled") || "Enabled"}
                    </Label>
                    <Switch
                      id="isEnabled"
                      checked={formData.isEnabled}
                      onCheckedChange={(checked) => updateFormData("isEnabled", checked)}
                    />
                  </div>
                </div>
              </div>
            </section>
          </form>
        </div>

        {/* Footer */}
        <SheetFooter className="px-6 py-4 border-t">
          <div className={`flex gap-3 w-full ${isRTL ? 'flex-row-reverse' : ''}`}>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
              className="flex-1"
            >
              {translate(t, "common.cancel") || "Cancel"}
            </Button>
            <Button
              type="submit"
              form="edit-job-form"
              disabled={isSubmitting || !isDirty}
              className="flex-1"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin me-2" />
                  {translate(t, "common.saving") || "Saving..."}
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 me-2" />
                  {translate(t, "common.save") || "Save Changes"}
                </>
              )}
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>

    {/* Close Confirmation Dialog */}
    <ConfirmationDialog
      open={showCloseConfirmDialog}
      onOpenChange={closeCloseDialog}
      onConfirm={handleCloseConfirm}
      isLoading={closeConfirmLoading}
      title={translate(t, "scheduler.confirmations.discardTitle") || "Discard Changes"}
      description={translate(t, "scheduler.confirmations.discardMessage") || "You have unsaved changes. Are you sure you want to close?"}
      confirmText={closeConfirmLabel}
      cancelText={closeCancelLabel}
      variant="destructive"
    />

    {/* Save Confirmation Dialog */}
    <ConfirmationDialog
      open={showSaveConfirmDialog}
      onOpenChange={closeSaveDialog}
      onConfirm={handleSaveConfirm}
      isLoading={saveConfirmLoading}
      title={translate(t, "scheduler.confirmations.updateTitle") || "Save Changes"}
      description={translate(t, "scheduler.confirmations.updateMessage") || "Are you sure you want to save these changes?"}
      confirmText={saveConfirmLabel}
      cancelText={saveCancelLabel}
    />
  </>
  );
}
