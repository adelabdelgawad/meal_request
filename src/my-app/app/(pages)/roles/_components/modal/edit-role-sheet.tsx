"use client";

import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/custom-toast";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import { useLanguage } from "@/hooks/use-language";
import { updateRole } from "@/lib/api/roles";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Edit } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import type {
  RoleResponse,
  RoleUpdateRequest,
  RoleValues,
} from "@/types/roles";

interface EditRoleSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role: RoleResponse;
  onSuccess?: () => void;
  onMutate?: () => void;
  onUpdate?: (updatedRole: RoleResponse) => void;
}

export function EditRoleSheet({
  open,
  onOpenChange,
  role,
  onSuccess,
  onMutate,
  onUpdate,
}: EditRoleSheetProps) {
  const { t, language } = useLanguage();
  const isRTL = language === "ar";

  // Type guard for translation structure
  type SettingRolesTranslations = {
    form?: Record<string, string>;
    messages?: Record<string, string>;
    validation?: Record<string, string>;
    confirmations?: Record<string, string>;
  };

  const settingRoles = (t as Record<string, unknown>).settingRoles as SettingRolesTranslations | undefined;
  const i18n = settingRoles?.form || {};
  const messages = settingRoles?.messages || {};
  const validation = settingRoles?.validation || {};
  const confirmations = settingRoles?.confirmations || {};

  // Form validation schema with localized messages
  const roleFormSchema = z.object({
    enName: z.string().min(1, validation.nameEnRequired || "English name is required"),
    arName: z.string().optional(),
    enDescription: z.string().optional(),
    arDescription: z.string().optional(),
  });

  type RoleFormData = z.infer<typeof roleFormSchema>;

  const [_isLoading, setIsLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Store original values for comparison
  const originalValues = useRef<RoleValues>({
    nameEn: "",
    nameAr: "",
    descriptionEn: "",
    descriptionAr: "",
  });

  const form = useForm<RoleFormData>({
    resolver: zodResolver(roleFormSchema),
    defaultValues: {
      enName: "",
      arName: "",
      enDescription: "",
      arDescription: "",
    },
  });

  // Initialize form and original values when sheet opens
  useEffect(() => {
    if (!open) {
      return;
    }

    const initialValues: RoleValues = {
      nameEn: role.nameEn || "",
      nameAr: role.nameAr || "",
      descriptionEn: role.descriptionEn || "",
      descriptionAr: role.descriptionAr || "",
    };

    // Store original values for comparison
    originalValues.current = { ...initialValues };

    // Reset form with current role data
    form.reset({
      enName: initialValues.nameEn,
      arName: initialValues.nameAr,
      enDescription: initialValues.descriptionEn,
      arDescription: initialValues.descriptionAr,
    });
    setHasChanges(false);
    setIsLoading(false);
  }, [open, role, form]);

  // Watch for form changes
  useEffect(() => {
    if (!open) {
      return;
    }

    const subscription = form.watch((values) => {
      const currentValues = {
        enName: values.enName || "",
        arName: values.arName || "",
        enDescription: values.enDescription || "",
        arDescription: values.arDescription || "",
      };

      const hasChanged =
        currentValues.enName !== originalValues.current.nameEn ||
        currentValues.arName !== originalValues.current.nameAr ||
        currentValues.enDescription !== originalValues.current.descriptionEn ||
        currentValues.arDescription !== originalValues.current.descriptionAr;

      setHasChanges(hasChanged);
    });

    return () => subscription.unsubscribe();
  }, [form, open]);

  const performSave = async () => {
    const formData = form.getValues();
    setIsLoading(true);

    try {
      // Ensure all values are strings and handle undefined cases
      const updatedValues: RoleValues = {
        nameEn: formData.enName || "",
        nameAr: formData.arName || "",
        descriptionEn: formData.enDescription || "",
        descriptionAr: formData.arDescription || "",
      };

      // Build the complete request structure
      const requestBody: RoleUpdateRequest = {
        nameEn: updatedValues.nameEn,
        nameAr: updatedValues.nameAr,
        descriptionEn: updatedValues.descriptionEn,
        descriptionAr: updatedValues.descriptionAr,
      };

      // Call API and get updated role _data
      const updatedRole = await updateRole(role.id, requestBody);

      toast.success(messages.updateSuccess || "Role updated successfully");

      // Update local state with returned _data
      if (onUpdate) {
        onUpdate(updatedRole);
      }
      if (onMutate) {
        await onMutate();
      }
      if (onSuccess) {
        onSuccess();
      }

      onOpenChange(false);
    } catch (error: unknown) {
      // Log technical error to console only
      console.error("Failed to update role:", error);
      // Show user-friendly error message
      toast.error(messages.updateError || "Failed to update role");
    } finally {
      setIsLoading(false);
    }
  };

  const performCancel = () => {
    form.reset();
    setHasChanges(false);
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

  const handleSave = async () => {
    const isValid = await form.trigger();
    if (!isValid) {
      toast.error(validation.fixErrors || "Please fix validation errors");
      return;
    }

    if (!hasChanges) {
      toast.info(messages.noChanges || "No changes to save");
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

  return (
    <>
      <Sheet open={open} onOpenChange={handleCancel}>
        <SheetContent
          className="sm:max-w-md"
          side="right"
        >
          <SheetHeader>
            <SheetTitle className={`flex items-center gap-3 ${isRTL ? 'flex-row-reverse' : ''}`}>
              <Edit className="h-5 w-5" />
              {i18n.editTitle || "Edit Role"}
            </SheetTitle>
            <SheetDescription>
              {i18n.editDescription || "Update role information and permissions."}
            </SheetDescription>
          </SheetHeader>

        <div className="grid gap-4 py-4">
          {/* English Name */}
          <div className="grid gap-2">
            <Label htmlFor="enName">
              {i18n.nameEn || "English Name"}{" "}
              <span className="text-red-500">*</span>
            </Label>
            <Input
              id="enName"
              {...form.register("enName")}
              placeholder={i18n.nameEnPlaceholder || "Enter English name"}
              disabled={_isLoading}
              className="rounded-none"
            />
            {form.formState.errors.enName && (
              <p className="text-sm text-red-500">
                {form.formState.errors.enName.message}
              </p>
            )}
          </div>

          {/* Arabic Name */}
          <div className="grid gap-2">
            <Label htmlFor="arName">{i18n.nameAr || "Arabic Name"}</Label>
            <Input
              id="arName"
              {...form.register("arName")}
              placeholder={i18n.nameArPlaceholder || "Enter Arabic name"}
              disabled={_isLoading}
              dir="rtl"
              className="rounded-none"
            />
          </div>

          {/* English Description */}
          <div className="grid gap-2">
            <Label htmlFor="enDescription">
              {i18n.descriptionEn || "English Description"}
            </Label>
            <Textarea
              id="enDescription"
              {...form.register("enDescription")}
              placeholder={
                i18n.descriptionEnPlaceholder || "Enter English description"
              }
              disabled={_isLoading}
              rows={3}
              className="rounded-none"
            />
          </div>

          {/* Arabic Description */}
          <div className="grid gap-2">
            <Label htmlFor="arDescription">
              {i18n.descriptionAr || "Arabic Description"}
            </Label>
            <Textarea
              id="arDescription"
              {...form.register("arDescription")}
              placeholder={
                i18n.descriptionArPlaceholder || "Enter Arabic description"
              }
              disabled={_isLoading}
              dir="rtl"
              rows={3}
              className="rounded-none"
            />
          </div>
        </div>

        <SheetFooter>
          <div className="flex flex-col-reverse sm:flex-row gap-3 w-full">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={_isLoading}
              className="flex-1 sm:flex-none min-w-[120px] h-10 rounded-none"
            >
              {i18n.cancel || "Cancel"}
            </Button>
            <Button
              type="button"
              onClick={handleSave}
              disabled={_isLoading || !hasChanges}
              className="flex-1 sm:flex-none min-w-[120px] h-10 rounded-none"
            >
              {_isLoading && <Loader2 className="h-4 w-4 animate-spin me-2" />}
              {i18n.save || "Save Changes"}
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
      title={confirmations.updateTitle || "Update Role"}
      description={confirmations.updateMessage || "Are you sure you want to update this role?"}
      confirmText={saveConfirmLabel}
      cancelText={saveCancelLabel}
    />

    {/* Cancel Confirmation Dialog */}
    <ConfirmationDialog
      open={showCancelConfirmDialog}
      onOpenChange={closeCancelDialog}
      onConfirm={handleCancelConfirm}
      isLoading={cancelConfirmLoading}
      title={confirmations.discardTitle || "Discard Changes"}
      description={confirmations.discardMessage || "Are you sure you want to discard your changes?"}
      confirmText={cancelConfirmLabel}
      cancelText={cancelCancelLabel}
      variant="destructive"
    />
    </>
  );
}
