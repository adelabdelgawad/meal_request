"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import Select, { MultiValue, components, type OptionProps, type StylesConfig } from "react-select";
import { useTheme } from "next-themes";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Edit, Loader2, Save, X, AlertCircle } from "lucide-react";
import { toast } from "@/components/ui/custom-toast";
import { useLanguage } from "@/hooks/use-language";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import { updateUserRoles, getUserSources, markUserAsManual, overrideUserStatus } from "@/lib/api/users";
import type { UserWithRolesResponse, UserSourceMetadata } from "@/types/users";
import { useRoles } from "../../context/users-actions-context";
import { UserSourceBadge } from "../user-source-badge";
import { UserOverrideIndicator } from "../user-override-indicator";

interface EditUserSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: UserWithRolesResponse;
  onSuccess: () => void;
  onUserUpdated?: (updatedUser: UserWithRolesResponse) => void;
}

type OptionType = {
  value: number;
  label: string;
  description: string;
};

type SourceOptionType = {
  value: string;
  label: string;
  description: string;
};

const CustomOption = (props: OptionProps<OptionType, true>) => {
  return (
    <components.Option {...props}>
      <div>
        <div style={{ fontWeight: 500 }}>{props.data.label}</div>
        {props.data.description && (
          <div className="text-sm text-muted-foreground">
            {props.data.description}
          </div>
        )}
      </div>
    </components.Option>
  );
};

function areRolesEqual(a: MultiValue<OptionType>, b: MultiValue<OptionType>) {
  if (a.length !== b.length) {
    return false;
  }
  const aIds = a.map((r) => r.value).sort();
  const bIds = b.map((r) => r.value).sort();
  return aIds.every((_id, idx) => _id === bIds[idx]);
}

export function EditUserSheet({
  open,
  onOpenChange,
  user,
  onSuccess,
  onUserUpdated,
}: EditUserSheetProps) {
  // Get roles from context and theme
  const roles = useRoles();
  const { resolvedTheme } = useTheme();
  const isDarkMode = resolvedTheme === "dark";

  const { t, language } = useLanguage();
  const isRTL = language === "ar";
  // Use translations from locale files
  const usersT = (t as Record<string, unknown>).users as Record<string, unknown> | undefined;
  const i18n = {
    edit: (usersT?.edit as Record<string, unknown>) || {},
    toast: (usersT?.toast as Record<string, unknown>) || {},
    columns: (usersT?.columns as Record<string, unknown>) || {},
  };

  const [selectedRoles, setSelectedRoles] = useState<MultiValue<OptionType>>(
    []
  );
  const [selectedSource, setSelectedSource] = useState<SourceOptionType | null>(null);
  const [statusOverride, setStatusOverride] = useState<boolean>(false);
  const [overrideReason, setOverrideReason] = useState<string>("");
  const [sourceChangeReason, setSourceChangeReason] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [userSources, setUserSources] = useState<UserSourceMetadata[]>([]);

  const closeSheet = () => {
    setSelectedRoles([]);
    setSelectedSource(null);
    setStatusOverride(false);
    setOverrideReason("");
    setSourceChangeReason("");
    setIsDirty(false);
    setIsMounted(false);
    onOpenChange(false);
  };

  const performSave = async () => {
    // Validate source change reason if source changed to manual
    const sourceChanged = selectedSource?.value !== initialValues.current.userSource;
    if (sourceChanged && selectedSource?.value === "manual" && (!sourceChangeReason || sourceChangeReason.trim().length < 20)) {
      toast.error((i18n.edit.validationSourceReason as string) || "Reason for marking user as manual must be at least 20 characters");
      return;
    }

    setIsLoading(true);

    try {
      let updatedUser: UserWithRolesResponse = user;

      // 1. Update roles if changed
      const rolesChanged = !areRolesEqual(selectedRoles, initialValues.current.roles);
      if (rolesChanged) {
        const updatedRoleIds = selectedRoles.map((role: OptionType) => role.value);
        updatedUser = await updateUserRoles(user.id, updatedRoleIds);
      }

      // 2. Update user source if changed to manual
      if (sourceChanged && selectedSource?.value === "manual") {
        updatedUser = await markUserAsManual(user.id, { reason: sourceChangeReason.trim() });
      }

      // 3. Update status override if changed (only for HRIS users)
      const overrideChanged = statusOverride !== initialValues.current.statusOverride;
      const overrideReasonChanged = overrideReason !== initialValues.current.overrideReason;
      const finalUserSource = sourceChanged ? selectedSource?.value : initialValues.current.userSource;

      // Only update override if the final user source is HRIS
      if (finalUserSource === "hris" && (overrideChanged || (statusOverride && overrideReasonChanged))) {
        const result = await overrideUserStatus(user.id, {
          statusOverride,
          overrideReason: statusOverride && overrideReason ? overrideReason.trim() : null,
        });
        updatedUser = result.user;
      }

      toast.success((i18n.toast.updateSuccess as string) || "User updated successfully");
      setIsDirty(false);
      onOpenChange(false);

      // Use the backend response directly - no need to construct locally
      if (onUserUpdated) {
        onUserUpdated(updatedUser);
      } else {
        onSuccess();
      }
    } catch (error) {
      // Log technical error to console only
      console.error("Failed to update user:", error);
      // Show user-friendly error message
      toast.error((i18n.toast.updateFailed as string) || "Failed to update user");
      throw error; // Re-throw to prevent dialog from closing
    } finally {
      setIsLoading(false);
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

  // Store initial values in a ref to avoid re-renders
  const initialValues = useRef<{
    roles: MultiValue<OptionType>;
    userSource: string;
    statusOverride: boolean;
    overrideReason: string;
  }>({
    roles: [],
    userSource: "",
    statusOverride: false,
    overrideReason: "",
  });

  // Fetch user sources on mount
  useEffect(() => {
    const fetchUserSources = async () => {
      try {
        const sources = await getUserSources();
        setUserSources(sources);
      } catch (error) {
        console.error("Failed to fetch user sources:", error);
        // Use fallback sources
        setUserSources([
          {
            code: "hris",
            nameEn: "HRIS User",
            nameAr: "مستخدم HRIS",
            descriptionEn: "User synchronized from the HRIS system",
            descriptionAr: "مستخدم متزامن من نظام الموارد البشرية",
            icon: "database",
            color: "blue",
            canOverride: true,
          },
          {
            code: "manual",
            nameEn: "Manual User",
            nameAr: "مستخدم يدوي",
            descriptionEn: "User created manually by an administrator",
            descriptionAr: "مستخدم تم إنشاؤه يدويًا بواسطة المسؤول",
            icon: "user-edit",
            color: "green",
            canOverride: false,
          },
        ]);
      }
    };
    fetchUserSources();
  }, []);

  // Create role options based on language - memoize to prevent recreation
  const options: OptionType[] = React.useMemo(
    () => {
      if (!roles || roles.length === 0) {
        return [];
      }
      return roles
        .filter((role) => role.isActive !== false) // Include if isActive is true or undefined
        .map((role) => ({
          value: role.id,
          label: language === "ar" && role.nameAr ? role.nameAr : role.nameEn,
          description:
            language === "ar" && role.descriptionAr
              ? role.descriptionAr
              : role.descriptionEn || "",
        }));
    },
    [roles, language]
  );

  // Create source options based on language - memoize to prevent recreation
  const sourceOptions: SourceOptionType[] = React.useMemo(
    () => {
      if (!userSources || userSources.length === 0) {
        return [];
      }
      return userSources.map((source) => ({
        value: source.code,
        label: language === "ar" ? source.nameAr : source.nameEn,
        description: language === "ar" ? source.descriptionAr : source.descriptionEn,
      }));
    },
    [userSources, language]
  );

  // Theme-aware styles for react-select (Roles - multi-select)
  const selectStyles: StylesConfig<OptionType, true> = useMemo(
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

  // Theme-aware styles for Source select (single-select with grey selection)
  const sourceSelectStyles: StylesConfig<SourceOptionType, false> = useMemo(
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
          ? isDarkMode ? "#27272a" : "#f4f4f5"  // Grey for selected (same as focused)
          : state.isFocused
          ? isDarkMode ? "#27272a" : "#f4f4f5"
          : isDarkMode ? "#18181b" : "#ffffff",
        color: isDarkMode ? "#fafafa" : "#09090b",  // Same text color for all states
        cursor: "pointer",
        "&:active": {
          backgroundColor: isDarkMode ? "#27272a" : "#e4e4e7",
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

  // Initialize form when sheet opens
  useEffect(() => {
    if (open && user) {
      setIsMounted(true);

      // Match user's roles by ID (roleIds array from backend)
      const userSelectedRoles = options.filter((option) => {
        // Primary: Match by role IDs array
        if (user.roleIds && Array.isArray(user.roleIds)) {
          return user.roleIds.includes(option.value);
        }
        // Fallback: Match by role names if roleIds not available
        if (user.roles && Array.isArray(user.roles)) {
          return user.roles.some((roleName: string) =>
            option.label === roleName
          );
        }
        // Last resort: Match by single roleId
        return user.roleId !== null && user.roleId === option.value;
      });
      setSelectedRoles(userSelectedRoles);

      // Set user source and override fields
      const currentUserSource = user.userSource || "hris";
      const currentStatusOverride = user.statusOverride || false;
      const currentOverrideReason = user.overrideReason || "";

      // Find and set the selected source option
      const userSourceOption = sourceOptions.find((option) => option.value === currentUserSource);
      setSelectedSource(userSourceOption || null);

      setStatusOverride(currentStatusOverride);
      setOverrideReason(currentOverrideReason);
      setSourceChangeReason("");

      initialValues.current = {
        roles: userSelectedRoles,
        userSource: currentUserSource,
        statusOverride: currentStatusOverride,
        overrideReason: currentOverrideReason,
      };

      setIsDirty(false);
    }
  }, [open, user, options, sourceOptions]);

  // Update selectedSource when sourceOptions loads and we have a stored userSource but no selected option
  useEffect(() => {
    if (
      isMounted &&
      sourceOptions.length > 0 &&
      !selectedSource &&
      initialValues.current.userSource
    ) {
      const userSourceOption = sourceOptions.find(
        (option) => option.value === initialValues.current.userSource
      );
      if (userSourceOption) {
        setSelectedSource(userSourceOption);
      }
    }
  }, [sourceOptions, selectedSource, isMounted]);

  // Efficient isDirty logic
  useEffect(() => {
    if (!isMounted) {
      return;
    }
    const rolesChanged = !areRolesEqual(selectedRoles, initialValues.current.roles);
    const sourceChanged = selectedSource?.value !== initialValues.current.userSource;
    const overrideChanged = statusOverride !== initialValues.current.statusOverride;
    const overrideReasonChanged = overrideReason !== initialValues.current.overrideReason;

    const dirty = rolesChanged || sourceChanged || overrideChanged || overrideReasonChanged;
    setIsDirty(dirty);
  }, [selectedRoles, selectedSource, statusOverride, overrideReason, isMounted]);

  const handleRoleChange = (newSelectedRoles: MultiValue<OptionType>) => {
    setSelectedRoles(newSelectedRoles);
  };

  const handleSourceChange = (newSource: SourceOptionType | null) => {
    setSelectedSource(newSource);

    // If changing to manual, disable override (manual users can't have override)
    if (newSource?.value === "manual" && statusOverride) {
      setStatusOverride(false);
      setOverrideReason("");
    }
  };

  const handleClose = () => {
    if (isDirty) {
      openCloseDialog();
      return;
    }
    closeSheet();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    openSaveDialog();
  };

  if (!isMounted) {
    return null;
  }

  return (
    <>
      <Sheet open={open} onOpenChange={handleClose}>
        <SheetContent
          className="w-full sm:max-w-2xl overflow-y-auto px-2"
          id="edit-user-sheet"
          side="right"
        >
          <SheetHeader>
            <SheetTitle className={`flex items-center justify-between ${isRTL ? 'flex-row-reverse' : ''}`}>
              <div className={`flex items-center gap-2 ${isRTL ? 'flex-row-reverse' : ''}`}>
                <Edit className="h-5 w-5" />
                {(i18n.edit.title as string) || "Edit User"}
              </div>
              {isDirty && (
                <span className="text-sm text-orange-600 font-normal">
                  • {(i18n.edit.unsavedChanges as string) || "Unsaved changes"}
                </span>
              )}
            </SheetTitle>
            <SheetDescription>
              {(i18n.edit.description as string) || "Edit user"}{" "}
              {user.username}
            </SheetDescription>
          </SheetHeader>

          {/* User Info Display */}
          <div className="grid grid-cols-1 gap-4 border p-4 bg-muted/50 text-sm sm:grid-cols-3 mt-6">
            <div>
              <Label className="text-muted-foreground">
                {(i18n.columns.username as string) || "Username"}
              </Label>
              <div>{user.username}</div>
            </div>
            <div>
              <Label className="text-muted-foreground">
                {(i18n.columns.fullName as string) || "Full Name"}
              </Label>
              <div>{user.fullName || "-"}</div>
            </div>
            <div>
              <Label className="text-muted-foreground">
                {(i18n.columns.title as string) || "Title"}
              </Label>
              <div>{user.title || "-"}</div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6 mt-6">
            <div className="space-y-4">
              {/* Roles */}
              <div className="space-y-2">
                <Label htmlFor="roles">{(i18n.edit.roles as string) || "Roles"}</Label>
                <Select<OptionType, true>
                  instanceId="user-roles-select"
                  options={options}
                  isMulti
                  onChange={handleRoleChange}
                  value={selectedRoles}
                  placeholder={(i18n.edit.selectRoles as string) || "Select roles"}
                  className="react-select-container"
                  classNamePrefix="react-select"
                  components={{
                    Option: CustomOption,
                  }}
                  isDisabled={isLoading}
                  menuPortalTarget={document.getElementById("edit-user-sheet")}
                  menuPosition="fixed"
                  styles={selectStyles}
                />
              </div>

              {/* User Source */}
              <div className="space-y-2">
                <Label htmlFor="userSource">{(i18n.columns.source as string) || "Source"}</Label>
                <Select<SourceOptionType, false>
                  instanceId="user-source-select"
                  options={sourceOptions}
                  onChange={handleSourceChange}
                  value={selectedSource}
                  placeholder={language === "ar" ? "اختر المصدر" : "Select source"}
                  noOptionsMessage={() => language === "ar" ? "لا توجد خيارات" : "No options"}
                  className="react-select-container"
                  classNamePrefix="react-select"
                  components={{
                    Option: CustomOption as unknown as React.ComponentType<OptionProps<SourceOptionType, false>>,
                  }}
                  isDisabled={isLoading || sourceOptions.length === 0}
                  isLoading={sourceOptions.length === 0}
                  menuPortalTarget={document.getElementById("edit-user-sheet")}
                  menuPosition="fixed"
                  styles={sourceSelectStyles}
                  isClearable={false}
                />
                {selectedSource?.value !== initialValues.current.userSource && selectedSource?.value === "manual" && (
                  <div className="space-y-2 mt-4 p-3 border border-amber-300 bg-amber-50 dark:bg-amber-950/20 rounded">
                    <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                      <AlertCircle className="w-4 h-4" />
                      <span className="text-sm font-medium">
                        {language === "ar" ? "سبب التغيير مطلوب" : "Reason Required"}
                      </span>
                    </div>
                    <Textarea
                      value={sourceChangeReason}
                      onChange={(e) => setSourceChangeReason(e.target.value)}
                      placeholder={language === "ar" ? "أدخل سبب تحويل المستخدم إلى يدوي (20 حرفًا على الأقل)" : "Enter reason for marking user as manual (min 20 characters)"}
                      disabled={isLoading}
                      rows={3}
                      className="text-sm"
                    />
                    <div className="text-xs text-muted-foreground">
                      {sourceChangeReason.length} / 20 {language === "ar" ? "حرف" : "characters"}
                    </div>
                  </div>
                )}
              </div>

              {/* Status Override */}
              {selectedSource?.value === "hris" && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="statusOverride" className="cursor-pointer">
                      {(i18n.columns.override as string) || "Status Override"}
                    </Label>
                    <Switch
                      id="statusOverride"
                      checked={statusOverride}
                      onCheckedChange={setStatusOverride}
                      disabled={isLoading}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {language === "ar"
                      ? "عند التفعيل، لن تقوم مزامنة HRIS بتعديل حالة نشاط هذا المستخدم"
                      : "When enabled, HRIS sync will not modify this user's active status"}
                  </p>
                  {statusOverride && (
                    <div className="space-y-2 mt-4">
                      <Label htmlFor="overrideReason" className="text-sm">
                        {language === "ar" ? "سبب الاستثناء (اختياري)" : "Override Reason (Optional)"}
                      </Label>
                      <Textarea
                        id="overrideReason"
                        value={overrideReason}
                        onChange={(e) => setOverrideReason(e.target.value)}
                        placeholder={language === "ar" ? "أدخل سبب استثناء الحالة (اختياري)" : "Enter reason for status override (optional)"}
                        disabled={isLoading}
                        rows={3}
                        className="text-sm"
                      />
                      <p className="text-xs text-muted-foreground">
                        {language === "ar"
                          ? "يمكنك تقديم تفسير لماذا يحتاج هذا المستخدم إلى استثناء"
                          : "You can provide an explanation for why this user needs an override"}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <SheetFooter className="pt-4">
              <div className={`flex justify-between items-center w-full ${isRTL ? 'flex-row-reverse' : ''}`}>
                <div className="text-sm text-gray-500">
                  {isDirty && ((i18n.edit.unsavedChanges as string) || "Unsaved changes")}
                </div>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleClose}
                    disabled={isLoading}
                  >
                    <X className="me-2 h-4 w-4" />
                    {(i18n.edit.cancel as string) || "Cancel"}
                  </Button>
                  <Button
                    type="submit"
                    disabled={isLoading || !isDirty}
                    className={isDirty ? "bg-primary" : ""}
                  >
                    {isLoading && (
                      <Loader2 className="me-2 h-4 w-4 animate-spin" />
                    )}
                    {!isLoading && <Save className="me-2 h-4 w-4" />}
                    {(i18n.edit.saveChanges as string) || "Save Changes"}
                  </Button>
                </div>
              </div>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>

      {/* Close Confirmation Dialog */}
      <ConfirmationDialog
        open={showCloseConfirmDialog}
        onOpenChange={closeCloseDialog}
        onConfirm={handleCloseConfirm}
        isLoading={closeConfirmLoading}
        title={(i18n.edit.confirmCloseTitle as string) || "Confirm Close"}
        description={(i18n.edit.unsavedChangesConfirm as string) || "You have unsaved changes. Are you sure you want to close?"}
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
        title={(i18n.edit.confirmSaveTitle as string) || "Confirm Save"}
        description={(i18n.edit.confirmSaveMessage as string) || "Are you sure you want to save these changes?"}
        confirmText={saveConfirmLabel}
        cancelText={saveCancelLabel}
      />
    </>
  );
}
