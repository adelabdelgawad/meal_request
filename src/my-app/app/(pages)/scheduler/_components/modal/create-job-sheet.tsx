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
import type { ScheduledJobCreate } from "@/types/scheduler";
import { useLanguage, translate } from "@/hooks/use-language";
import { useSchedulerLookupData } from "../../context/scheduler-actions-context";
import {
  Timer,
  Loader2,
  Plus,
  Clock,
  Calendar,
  Settings,
  Code,
} from "lucide-react";

interface CreateJobSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateJob: (data: ScheduledJobCreate) => Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }>;
  onSuccess: () => void;
}

const defaultFormData: ScheduledJobCreate = {
  taskFunctionId: 0,
  jobTypeId: 0,
  nameEn: "",
  nameAr: "",
  descriptionEn: "",
  descriptionAr: "",
  intervalMinutes: 30,
  priority: 0,
  maxInstances: 1,
  misfireGraceTime: 300,
  coalesce: true,
  isEnabled: true,
};

export function CreateJobSheet({
  open,
  onOpenChange,
  onCreateJob,
  onSuccess,
}: CreateJobSheetProps) {
  const { t, dir, language } = useLanguage();
  const isRTL = dir === "rtl";

  // Get pre-loaded lookup data from context
  const { taskFunctions, jobTypes } = useSchedulerLookupData();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState<ScheduledJobCreate>(defaultFormData);
  const [selectedJobTypeCode, setSelectedJobTypeCode] = useState<string>("interval");
  const [hasChanges, setHasChanges] = useState(false);

  // Store original form data for change tracking
  const originalFormData = useRef<ScheduledJobCreate>(defaultFormData);

  // Reset form to initial state
  const resetForm = useCallback(() => {
    const resetData = { ...defaultFormData };
    setFormData(resetData);
    originalFormData.current = resetData;
    setSelectedJobTypeCode("interval");
    setHasChanges(false);
    setIsSubmitting(false);
  }, []);

  // Check if form has changes
  const checkForChanges = useCallback((currentData: ScheduledJobCreate) => {
    const original = originalFormData.current;

    // Check all relevant fields
    return (
      currentData.taskFunctionId !== original.taskFunctionId ||
      currentData.jobTypeId !== original.jobTypeId ||
      currentData.nameEn !== original.nameEn ||
      currentData.nameAr !== original.nameAr ||
      currentData.descriptionEn !== original.descriptionEn ||
      currentData.descriptionAr !== original.descriptionAr ||
      currentData.intervalSeconds !== original.intervalSeconds ||
      currentData.intervalMinutes !== original.intervalMinutes ||
      currentData.intervalHours !== original.intervalHours ||
      currentData.intervalDays !== original.intervalDays ||
      currentData.cronExpression !== original.cronExpression ||
      currentData.priority !== original.priority ||
      currentData.maxInstances !== original.maxInstances ||
      currentData.misfireGraceTime !== original.misfireGraceTime ||
      currentData.coalesce !== original.coalesce ||
      currentData.isEnabled !== original.isEnabled
    );
  }, []);

  // Update hasChanges when form data changes
  useEffect(() => {
    const changes = checkForChanges(formData);
    setHasChanges(changes);
  }, [formData, checkForChanges]);

  // Reset form when sheet opens and set default job type
  useEffect(() => {
    if (open) {
      resetForm();

      // Set default job type (interval) if available
      const intervalType = jobTypes.find((jt) => jt.code === "interval");
      if (intervalType && !formData.jobTypeId) {
        setFormData((prev) => ({ ...prev, jobTypeId: intervalType.id }));
        setSelectedJobTypeCode("interval");
      }
    }
  }, [open, resetForm, jobTypes, formData.jobTypeId]);

  // Perform save action
  const performSave = async () => {
    setIsSubmitting(true);

    try {
      const dataToSubmit: ScheduledJobCreate = { ...formData };

      // Clear interval fields if using cron
      if (selectedJobTypeCode === "cron") {
        dataToSubmit.intervalSeconds = undefined;
        dataToSubmit.intervalMinutes = undefined;
        dataToSubmit.intervalHours = undefined;
        dataToSubmit.intervalDays = undefined;
      } else {
        dataToSubmit.cronExpression = undefined;
      }

      const result = await onCreateJob(dataToSubmit);

      if (result.success) {
        toast.success(result.message || translate(t, "scheduler.toast.createSuccess") || "Job created successfully");
        resetForm();
        onSuccess();
        onOpenChange(false);
      } else {
        toast.error(result.error || translate(t, "scheduler.toast.createError") || "Failed to create job");
        throw new Error(result.error); // Prevent dialog from closing
      }
    } catch (error) {
      console.error("Failed to create job:", error);
      toast.error(translate(t, "scheduler.toast.createError") || "Failed to create job");
      throw error; // Re-throw to prevent dialog from closing
    } finally {
      setIsSubmitting(false);
    }
  };

  // Perform cancel action
  const performCancel = () => {
    resetForm();
    onOpenChange(false);
  };

  // Confirmation dialogs
  const {
    isOpen: showSaveConfirmDialog,
    isLoading: saveConfirmLoading,
    open: openSaveDialog,
    close: closeSaveDialog,
    confirm: handleSaveConfirm,
    confirmLabel: saveConfirmLabel,
    cancelLabel: saveCancelLabel,
  } = useConfirmationDialog(performSave);

  const {
    isOpen: showCancelConfirmDialog,
    isLoading: cancelConfirmLoading,
    open: openCancelDialog,
    close: closeCancelDialog,
    confirm: handleCancelConfirm,
    confirmLabel: cancelConfirmLabel,
    cancelLabel: cancelCancelLabel,
  } = useConfirmationDialog(performCancel);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!formData.taskFunctionId) {
      toast.error(translate(t, "scheduler.validation.taskFunctionRequired") || "Please select a task function");
      return;
    }
    if (!formData.jobTypeId) {
      toast.error(translate(t, "scheduler.validation.jobTypeRequired") || "Please select a job type");
      return;
    }

    openSaveDialog();
  };

  const handleCancel = () => {
    if (hasChanges) {
      openCancelDialog();
    } else {
      performCancel();
    }
  };

  const updateFormData = (field: keyof ScheduledJobCreate, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleJobTypeChange = (jobTypeId: string) => {
    const id = parseInt(jobTypeId);
    updateFormData("jobTypeId", id);
    const jobType = jobTypes.find((jt) => jt.id === id);
    if (jobType) {
      setSelectedJobTypeCode(jobType.code);
    }
  };

  const getLocalizedName = (item: { nameEn: string; nameAr: string }) => {
    return language === "ar" ? item.nameAr : item.nameEn;
  };

  return (
    <>
      <Sheet open={open} onOpenChange={handleCancel}>
        <SheetContent
          side={isRTL ? "left" : "right"}
          className="w-full sm:max-w-lg flex flex-col p-0"
        >
          {/* Header */}
          <SheetHeader className="px-4 pt-4 pb-2 shrink-0 border-b">
            <SheetTitle className={`flex items-center justify-between text-base ${isRTL ? "flex-row-reverse" : ""}`}>
              <div className={`flex items-center gap-2 ${isRTL ? "flex-row-reverse" : ""}`}>
                <div className="p-1 bg-primary/10">
                  <Plus className="h-3.5 w-3.5 text-primary" />
                </div>
                {translate(t, "scheduler.create.title") || "Add Schedule"}
              </div>
              {hasChanges && (
                <span className="text-sm text-orange-600 font-normal">
                  • {translate(t, "scheduler.unsavedChanges") || "Unsaved changes"}
                </span>
              )}
            </SheetTitle>
            <SheetDescription className="text-xs">
              {translate(t, "scheduler.create.description") || "Create a new scheduled job"}
            </SheetDescription>
          </SheetHeader>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          <form id="create-job-form" onSubmit={handleSubmit} className="space-y-3">
              {/* Task Function Selection */}
              <section>
                <h3 className="text-xs font-semibold flex items-center gap-1.5 mb-2 text-muted-foreground uppercase tracking-wide">
                  <Code className="h-3 w-3" />
                  {translate(t, "scheduler.create.taskSection") || "Task Function"}
                </h3>
                <div className="p-2 bg-muted/50 border space-y-1">
                  <Label htmlFor="taskFunction" className="text-[10px] text-muted-foreground uppercase">
                    {translate(t, "scheduler.fields.taskFunction") || "Task Function"} *
                  </Label>
                  <Select
                    value={formData.taskFunctionId ? formData.taskFunctionId.toString() : ""}
                    onValueChange={(value) => updateFormData("taskFunctionId", parseInt(value))}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder={translate(t, "scheduler.placeholders.selectTask") || "Select a task..."} />
                    </SelectTrigger>
                    <SelectContent>
                      {taskFunctions.map((tf) => (
                        <SelectItem key={tf.id} value={tf.id.toString()} className="text-xs">
                          <div className="flex flex-col">
                            <span className="font-medium">{getLocalizedName(tf)}</span>
                            <span className="text-[10px] text-muted-foreground font-mono">{tf.key}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </section>

              <Separator />

              {/* Name & Description Section */}
              <section>
                <h3 className="text-xs font-semibold flex items-center gap-1.5 mb-2 text-muted-foreground uppercase tracking-wide">
                  <Timer className="h-3 w-3" />
                  {translate(t, "scheduler.edit.nameSection") || "Name & Description (Optional Override)"}
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
                        placeholder="Optional override..."
                        className="h-7 text-xs"
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
                        placeholder="تجاوز اختياري..."
                        className="h-7 text-xs"
                        dir="rtl"
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
                  {selectedJobTypeCode === "cron" ? (
                    <Calendar className="h-3 w-3" />
                  ) : (
                    <Clock className="h-3 w-3" />
                  )}
                  {translate(t, "scheduler.edit.scheduleSection") || "Schedule"}
                </h3>
                <div className="space-y-2">
                  <div className="p-2 bg-muted/50 border space-y-1">
                    <Label htmlFor="jobType" className="text-[10px] text-muted-foreground uppercase">
                      {translate(t, "scheduler.fields.type") || "Type"} *
                    </Label>
                    <Select
                      value={formData.jobTypeId ? formData.jobTypeId.toString() : ""}
                      onValueChange={handleJobTypeChange}
                    >
                      <SelectTrigger className="h-7 text-xs">
                        <SelectValue placeholder={translate(t, "scheduler.placeholders.selectType") || "Select type..."} />
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
                              {getLocalizedName(jt)}
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {selectedJobTypeCode === "interval" ? (
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
                  ) : selectedJobTypeCode === "cron" ? (
                    <div className="p-2 bg-muted/50 border space-y-1">
                      <Label htmlFor="cronExpression" className="text-[10px] text-muted-foreground uppercase">
                        {translate(t, "scheduler.fields.cronExpression") || "Cron Expression"}
                      </Label>
                      <Input
                        id="cronExpression"
                        value={formData.cronExpression || ""}
                        onChange={(e) => updateFormData("cronExpression", e.target.value)}
                        placeholder="0 * * * *"
                        className="font-mono h-7 text-xs"
                      />
                      <p className="text-[10px] text-muted-foreground">
                        {translate(t, "scheduler.edit.cronHelp") || "minute hour day month weekday"}
                      </p>
                    </div>
                  ) : null}
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
                        value={formData.priority ?? 0}
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
                        value={formData.maxInstances ?? 1}
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
                        value={formData.misfireGraceTime ?? 300}
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
                        checked={formData.coalesce ?? true}
                        onCheckedChange={(checked) => updateFormData("coalesce", checked)}
                      />
                    </div>
                    <div className="flex items-center justify-between p-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                      <Label htmlFor="isEnabled" className="text-xs font-medium">
                        {translate(t, "scheduler.fields.enabled") || "Enabled"}
                      </Label>
                      <Switch
                        id="isEnabled"
                        checked={formData.isEnabled ?? true}
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
              onClick={handleCancel}
              disabled={isSubmitting}
              className="flex-1"
            >
              {translate(t, "common.cancel") || "Cancel"}
            </Button>
            <Button
              type="submit"
              form="create-job-form"
              disabled={isSubmitting || !formData.taskFunctionId || !formData.jobTypeId}
              className="flex-1"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin me-2" />
                  {translate(t, "common.creating") || "Creating..."}
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 me-2" />
                  {translate(t, "common.create") || "Create"}
                </>
              )}
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>

    {/* Save Confirmation Dialog */}
    <ConfirmationDialog
      open={showSaveConfirmDialog}
      onOpenChange={closeSaveDialog}
      onConfirm={handleSaveConfirm}
      isLoading={saveConfirmLoading}
      title={translate(t, "scheduler.confirmations.createTitle") || "Create Job"}
      description={translate(t, "scheduler.confirmations.createMessage") || "Are you sure you want to create this scheduled job?"}
      confirmText={saveConfirmLabel}
      cancelText={saveCancelLabel}
    />

    {/* Cancel Confirmation Dialog */}
    <ConfirmationDialog
      open={showCancelConfirmDialog}
      onOpenChange={closeCancelDialog}
      onConfirm={handleCancelConfirm}
      isLoading={cancelConfirmLoading}
      title={translate(t, "scheduler.confirmations.discardTitle") || "Discard Changes"}
      description={translate(t, "scheduler.confirmations.discardMessage") || "Are you sure you want to discard your changes?"}
      confirmText={cancelConfirmLabel}
      cancelText={cancelCancelLabel}
      variant="destructive"
    />
  </>
  );
}
