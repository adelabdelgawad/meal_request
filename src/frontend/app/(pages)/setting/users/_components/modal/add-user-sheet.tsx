// components/users/add-user-sheet.tsx
"use client";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/custom-toast";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import { useLanguage } from "@/hooks/use-language";
import { Loader2, Plus, User, Users } from "lucide-react";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Select, { type StylesConfig } from "react-select";
import { useTheme } from "next-themes";
import { DomainUserSelector } from "@/components/ui/domain-user-selector";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import type { UserCreate } from "@/types/users";
import type { DomainUser } from "@/types/domain-users";
import { useRoles } from "../../context/users-actions-context";

interface FormData {
  selectedUser: DomainUser | null;
  selectedRoles: RoleOption[];
}

interface AddUserSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (user: UserCreate) => Promise<void>;
}

type RoleOption = {
  value: number;
  label: string;
  description?: string;
};

const initialFormData: FormData = {
  selectedUser: null,
  selectedRoles: [],
};

export function AddUserSheet({
  open,
  onOpenChange,
  onSave,
}: AddUserSheetProps) {
  // Get roles from context
  const roles = useRoles();
  const { resolvedTheme } = useTheme();
  const isDarkMode = resolvedTheme === "dark";

  const { t, language } = useLanguage();
  const isRTL = language === "ar";

  // Use translations from locale files
  const usersT = (t as Record<string, unknown>).users as Record<string, unknown> | undefined;
  const i18n = (usersT?.add as Record<string, unknown>) || {};
  const confirmationsI18n = (i18n.confirmations as Record<string, unknown>) || {};
  const validationI18n = (i18n.validation as Record<string, unknown>) || {};
  const toastI18n = (usersT?.toast as Record<string, unknown>) || {};

  // Create the performSave function separately:
  const performSave = async () => {
    setIsSubmitting(true);

    try {
      const roleIds = formData.selectedRoles.map((role) => role.value);

      const userToCreate: UserCreate = {
        username: formData.selectedUser!.username,
        email: formData.selectedUser!.email ?? undefined,
        fullName: formData.selectedUser!.fullName ?? undefined,
        title: formData.selectedUser!.title ?? formData.selectedUser!.office ?? undefined,
        roleId: roleIds[0], // Use first role for roleId field
      };

      await onSave(userToCreate);

      // Show success toast with localized message
      toast.success((toastI18n.createSuccess as string) || "User created successfully");

      resetForm();
      onOpenChange(false);
    } catch (error) {
      // Log technical error to console only
      console.error("Failed to create user:", error);
      // Show user-friendly error message
      toast.error((toastI18n.createFailed as string) || "Failed to create user");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Create the performCancel function separately:
  const performCancel = () => {
    resetForm();
    onOpenChange(false);
  };

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

  const originalFormData = useRef<FormData>(initialFormData);

  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [hasChanges, setHasChanges] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Create role options with proper array check
  const roleOptions: RoleOption[] = React.useMemo(() => {
    if (!Array.isArray(roles)) {
      return [];
    }

    return roles
      .filter((role) => role.isActive ?? true)
      .map((role) => ({
        value: role.id,
        label:
          language === "ar" && role.nameAr
            ? role.nameAr
            : role.nameEn || "Unknown Role",
        description:
          language === "ar" && role.descriptionAr
            ? role.descriptionAr
            : role.descriptionEn || undefined,
      }));
  }, [roles, language]);

  // Theme-aware styles for react-select
  const selectStyles: StylesConfig<RoleOption, true> = useMemo(
    () => ({
      control: (base, state) => ({
        ...base,
        borderRadius: 0,
        backgroundColor: isDarkMode ? "#09090b" : "#ffffff",
        borderColor: state.isFocused
          ? isDarkMode ? "#3b82f6" : "#2563eb"
          : isDarkMode ? "#27272a" : "#e4e4e7",
        boxShadow: state.isFocused ? `0 0 0 1px ${isDarkMode ? "#3b82f6" : "#2563eb"}` : "none",
        "&:hover": {
          borderColor: isDarkMode ? "#3b82f6" : "#2563eb",
        },
      }),
      menu: (base) => ({
        ...base,
        borderRadius: 0,
        backgroundColor: isDarkMode ? "#18181b" : "#ffffff",
        border: `1px solid ${isDarkMode ? "#27272a" : "#e4e4e7"}`,
        zIndex: 9999,
      }),
      menuList: (base) => ({
        ...base,
        padding: 0,
        backgroundColor: isDarkMode ? "#18181b" : "#ffffff",
      }),
      option: (base, state) => ({
        ...base,
        backgroundColor: state.isSelected
          ? isDarkMode ? "#3b82f6" : "#2563eb"
          : state.isFocused
          ? isDarkMode ? "#27272a" : "#f4f4f5"
          : isDarkMode ? "#18181b" : "#ffffff",
        color: state.isSelected
          ? "#ffffff"
          : isDarkMode ? "#fafafa" : "#09090b",
        cursor: "pointer",
        "&:active": {
          backgroundColor: isDarkMode ? "#27272a" : "#e4e4e7",
        },
      }),
      multiValue: (base) => ({
        ...base,
        borderRadius: 0,
        backgroundColor: isDarkMode ? "#27272a" : "#f4f4f5",
      }),
      multiValueLabel: (base) => ({
        ...base,
        color: isDarkMode ? "#fafafa" : "#09090b",
      }),
      multiValueRemove: (base) => ({
        ...base,
        color: isDarkMode ? "#a1a1aa" : "#71717a",
        "&:hover": {
          backgroundColor: isDarkMode ? "#dc2626" : "#ef4444",
          color: "#ffffff",
        },
      }),
      input: (base) => ({
        ...base,
        color: isDarkMode ? "#fafafa" : "#09090b",
      }),
      placeholder: (base) => ({
        ...base,
        color: isDarkMode ? "#71717a" : "#a1a1aa",
      }),
      singleValue: (base) => ({
        ...base,
        color: isDarkMode ? "#fafafa" : "#09090b",
      }),
      menuPortal: (base) => ({
        ...base,
        zIndex: 9999,
      }),
      noOptionsMessage: (base) => ({
        ...base,
        backgroundColor: isDarkMode ? "#18181b" : "#ffffff",
        color: isDarkMode ? "#a1a1aa" : "#71717a",
      }),
    }),
    [isDarkMode]
  );

  const resetForm = useCallback(() => {
    const resetData = { ...initialFormData };
    setFormData(resetData);
    originalFormData.current = resetData;
    setHasChanges(false);
    setIsSubmitting(false);
  }, []);

  // Check if form has changes
  const checkForChanges = useCallback((currentData: FormData) => {
    const hasUserChanged =
      currentData.selectedUser?.username !==
      originalFormData.current.selectedUser?.username;
    const hasRolesChanged =
      currentData.selectedRoles.length !==
        originalFormData.current.selectedRoles.length ||
      currentData.selectedRoles.some(
        (role) =>
          !originalFormData.current.selectedRoles.find(
            (originalRole) => originalRole.value === role.value
          )
      );

    return hasUserChanged || hasRolesChanged;
  }, []);

  // Update hasChanges when form _data changes
  useEffect(() => {
    const changes = checkForChanges(formData);
    setHasChanges(changes);
  }, [formData, checkForChanges]);

  // Reset form when sheet opens
  useEffect(() => {
    if (open) {
      resetForm();
    }
  }, [open, resetForm]);

  const handleUserSelect = useCallback((user: DomainUser | null) => {
    setFormData((prev) => ({ ...prev, selectedUser: user }));
  }, []);

  const handleRoleSelect = useCallback((options: unknown) => {
    const multiOptions = options as RoleOption[] | null;
    setFormData((prev) => ({
      ...prev,
      selectedRoles: multiOptions ? [...multiOptions] : [],
    }));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.selectedUser || formData.selectedRoles.length === 0) {
      toast.error(
        (validationI18n.allFieldsRequired as string) || "All fields are required"
      );
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
          className="w-full sm:max-w-md flex flex-col p-0"
          side="right"
        >
          {/* Header */}
          <SheetHeader className="px-6 py-4 border-b">
            <SheetTitle className={`flex items-center justify-between ${isRTL ? 'flex-row-reverse' : ''}`}>
              <div className={`flex items-center gap-2 ${isRTL ? 'flex-row-reverse' : ''}`}>
                <Plus className="h-5 w-5" />
                {(i18n.title as string) || "Add User"}
              </div>
              {hasChanges && (
                <span className="text-sm text-orange-600 font-normal">
                  • {(i18n.unsavedChanges as string) || "Unsaved changes"}
                </span>
              )}
            </SheetTitle>
            <SheetDescription className="text-sm text-muted-foreground">
              {(i18n.description as string) || "Add a new user to the system"}
            </SheetDescription>
          </SheetHeader>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5">
            {/* User Selection */}
            <div className="space-y-2">
              <Label className={`flex items-center gap-2 text-sm font-medium ${isRTL ? 'flex-row-reverse' : ''}`}>
                <User className="h-4 w-4 text-muted-foreground" />
                {(i18n.selectUser as string) || "Select User"}
                <span className="text-destructive">*</span>
              </Label>
              <div dir="ltr">
                <DomainUserSelector
                  value={formData.selectedUser}
                  onSelect={handleUserSelect}
                  placeholder={(i18n.selectUserPlaceholder as string) || "Search and select a user..."}
                  searchPlaceholder={(i18n.searchUsers as string) || "Search by name or username..."}
                  emptyText={(i18n.noUsersAvailable as string) || "No users found"}
                  errorText={(i18n.errorLoadingUsers as string) || "Failed to load users"}
                  disabled={isSubmitting}
                />
              </div>
            </div>

            {/* Roles Selection */}
            <div className="space-y-2">
              <Label className={`flex items-center gap-2 text-sm font-medium ${isRTL ? 'flex-row-reverse' : ''}`}>
                <Users className="h-4 w-4 text-muted-foreground" />
                {(i18n.roles as string) || "Roles"}
                <span className="text-destructive">*</span>
                {formData.selectedRoles.length > 0 && (
                  <span className="text-xs text-muted-foreground font-normal ms-auto">
                    {formData.selectedRoles.length} {(i18n.selected as string) || "selected"}
                  </span>
                )}
              </Label>
              <div dir="ltr">
                <Select<RoleOption, true>
                  options={roleOptions}
                  value={formData.selectedRoles}
                  onChange={handleRoleSelect}
                  isMulti
                  isSearchable
                  placeholder={(i18n.rolesPlaceholder as string) || "Select roles..."}
                  className="react-select-container"
                  classNamePrefix="react-select"
                  isDisabled={isSubmitting}
                  styles={selectStyles}
                  noOptionsMessage={({ inputValue }: { inputValue: string }) =>
                    inputValue
                      ? ((i18n.noRolesFound as string) || "No roles found matching {search}").replace("{search}", inputValue)
                      : (i18n.noRolesAvailable as string) || "No roles available"
                  }
                />
              </div>
            </div>
          </div>

          {/* Footer */}
          <SheetFooter className="px-6 py-4 border-t">
            <div className={`flex gap-3 w-full ${isRTL ? 'flex-row-reverse' : ''}`}>
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={isSubmitting}
                className="flex-1"
              >
                {(i18n.cancel as string) || "Cancel"}
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!formData.selectedUser || formData.selectedRoles.length === 0 || isSubmitting}
                className="flex-1"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin me-2" />
                    {(i18n.creating as string) || "Creating..."}
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 me-2" />
                    {(i18n.create as string) || "Create"}
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
        title={(confirmationsI18n.createTitle as string) || "Create User"}
        description={(confirmationsI18n.createMessage as string) || "Are you sure you want to create this user?"}
        confirmText={saveConfirmLabel}
        cancelText={saveCancelLabel}
      />

      <ConfirmationDialog
        open={showCancelConfirmDialog}
        onOpenChange={closeCancelDialog}
        onConfirm={handleCancelConfirm}
        isLoading={cancelConfirmLoading}
        title={(confirmationsI18n.discardTitle as string) || "Discard Changes"}
        description={(confirmationsI18n.discardMessage as string) || "Are you sure you want to discard your changes?"}
        confirmText={cancelConfirmLabel}
        cancelText={cancelCancelLabel}
        variant="destructive"
      />
    </>
  );
}
