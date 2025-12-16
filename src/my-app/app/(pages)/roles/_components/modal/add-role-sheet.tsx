"use client";

import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/custom-toast";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
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
import { createRole } from "@/lib/api/roles";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Plus } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import type { RoleCreateRequest } from "@/types/roles";

interface AddRoleSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onMutate?: () => void;
  onSuccess?: () => void;
}

export function AddRoleSheet({
  open,
  onOpenChange,
  onMutate,
  onSuccess,
}: AddRoleSheetProps) {
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

  // Create dynamic schema with localized messages
  const createRoleSchema = z.object({
    enName: z
      .string()
      .min(1, validation.nameEnRequired || "English name is required")
      .max(100, validation.nameEnMaxLength || "English name must be 100 characters or less"),
    arName: z
      .string()
      .max(100, validation.nameArMaxLength || "Arabic name must be 100 characters or less")
      .optional(),
    enDescription: z
      .string()
      .max(500, validation.descriptionMaxLength || "Description must be 500 characters or less")
      .optional(),
    arDescription: z
      .string()
      .max(500, validation.descriptionMaxLength || "Description must be 500 characters or less")
      .optional(),
  });

  type CreateRoleFormData = z.infer<typeof createRoleSchema>;

  const form = useForm<CreateRoleFormData>({
    resolver: zodResolver(createRoleSchema),
    mode: "onChange",
    defaultValues: {
      enName: "",
      arName: "",
      enDescription: "",
      arDescription: "",
    },
  });

  const [isLoading, setIsLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Watch form changes
  useEffect(() => {
    const subscription = form.watch((values) => {
      const changed = !!(
        values.enName ||
        values.arName ||
        values.enDescription ||
        values.arDescription
      );
      setHasChanges(changed);
    });
    return () => subscription.unsubscribe();
  }, [form]);

  // Reset form callback
  const resetForm = useCallback(() => {
    form.reset({
      enName: "",
      arName: "",
      enDescription: "",
      arDescription: "",
    });
    setHasChanges(false);
  }, [form]);

  // Reset form when sheet opens
  useEffect(() => {
    if (open) {
      resetForm();
    }
  }, [open, resetForm]);

  // Create performSave function
  const performSave = async () => {
    setIsLoading(true);
    try {
      const formValues = form.getValues();
      const roleData: RoleCreateRequest = {
        nameEn: formValues.enName,
        nameAr: formValues.arName || "",
        descriptionEn: formValues.enDescription || null,
        descriptionAr: formValues.arDescription || null,
      };

      await createRole(roleData);
      toast.success(messages.createSuccess || "Role created successfully");

      if (onMutate) {
        onMutate();
      }
      if (onSuccess) {
        onSuccess();
      }

      resetForm();
      onOpenChange(false);
    } catch (error: unknown) {
      // Log technical error to console only
      console.error("Failed to create role:", error);
      // Show user-friendly error message
      toast.error(messages.createError || "Failed to create role");
    } finally {
      setIsLoading(false);
    }
  };

  // Create performCancel function
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
    const isValid = await form.trigger();
    if (!isValid) {
      toast.error(validation.fixErrors || "Please fix validation errors");
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
          className="w-full sm:max-w-2xl"
          side="right"
        >
          <SheetHeader>
            <SheetTitle className={`flex items-center gap-3 ${isRTL ? 'flex-row-reverse' : ''}`}>
              <Plus className="h-5 w-5" />
              {i18n.createTitle || "Add Role"}
            </SheetTitle>
            <SheetDescription>{i18n.createDescription || "Create a new role in the system"}</SheetDescription>
          </SheetHeader>

          <Form {...form}>
            <form
              onSubmit={handleSubmit}
              className="space-y-4 p-4"
            >
              <FormField
                control={form.control}
                name="enName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      {i18n.nameEn || "English Name"}{" "}
                      <span className="text-red-500">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder={i18n.nameEnPlaceholder || "Enter role name in English"}
                        disabled={isLoading}
                        className="rounded-none"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="arName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{i18n.nameAr || "Arabic Name"}</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder={i18n.nameArPlaceholder || "Enter role name in Arabic"}
                        disabled={isLoading}
                        dir="rtl"
                        className="rounded-none"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="enDescription"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{i18n.descriptionEn || "English Description"}</FormLabel>
                    <FormControl>
                      <Textarea
                        {...field}
                        placeholder={i18n.descriptionEnPlaceholder || "Enter description in English (optional)"}
                        disabled={isLoading}
                        rows={3}
                        className="rounded-none"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="arDescription"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{i18n.descriptionAr || "Arabic Description"}</FormLabel>
                    <FormControl>
                      <Textarea
                        {...field}
                        placeholder={i18n.descriptionArPlaceholder || "Enter description in Arabic (optional)"}
                        disabled={isLoading}
                        dir="rtl"
                        rows={3}
                        className="rounded-none"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <SheetFooter>
                <div className="flex flex-col-reverse sm:flex-row gap-3 w-full">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleCancel}
                    disabled={isLoading}
                    className="flex-1 sm:flex-none min-w-[120px] h-10 rounded-none"
                  >
                    {i18n.cancel || "Cancel"}
                  </Button>
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="flex-1 sm:flex-none min-w-[120px] h-10 rounded-none"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin me-2" />
                        {i18n.creating || "Creating..."}
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 me-2" />
                        {i18n.create || "Create"}
                      </>
                    )}
                  </Button>
                </div>
              </SheetFooter>
            </form>
          </Form>
        </SheetContent>
      </Sheet>

      {/* Save Confirmation Dialog */}
      <ConfirmationDialog
        open={showSaveConfirmDialog}
        onOpenChange={closeSaveDialog}
        onConfirm={handleSaveConfirm}
        isLoading={saveConfirmLoading}
        title={confirmations.createTitle || "Create Role"}
        description={confirmations.createMessage || "Are you sure you want to create this role?"}
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
