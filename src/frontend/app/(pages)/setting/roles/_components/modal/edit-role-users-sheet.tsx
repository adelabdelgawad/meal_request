/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Label } from "@/components/ui/label";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import { useLanguage } from "@/hooks/use-language";
import { Loader2, Users } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "@/components/ui/custom-toast";
import Select, { MultiValue, components, OptionProps } from "react-select";
import { fetchRoleUsers, updateRoleUsers } from "@/lib/api/roles";
import type { RoleResponse, RoleUserInfo } from "@/types/roles";
import type { UserResponse } from "@/types/users";

interface UserOptionType {
  value: string; // User ID (UUID)
  label: string;
  username: string;
  email?: string | null;
}

interface EditRoleUsersSheetProps {
  role: RoleResponse;
  preloadedUsers: UserResponse[];
  onMutate?: () => void;
  onSuccess?: () => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const CustomUserOption = (props: OptionProps<UserOptionType, true>) => {
  return (
    <components.Option {...props}>
      <div>
        <div className="font-medium">{props.data.label}</div>
        {props.data.email && (
          <div className="text-xs text-muted-foreground">{props.data.email}</div>
        )}
      </div>
    </components.Option>
  );
};

export function EditRoleUsersSheet({
  role,
  preloadedUsers,
  onMutate,
  onSuccess,
  open,
  onOpenChange,
}: EditRoleUsersSheetProps) {
  const { t, language } = useLanguage();
  const isRTL = language === "ar";
  // Use type assertion and optional chaining to handle incomplete translations
  const settingRoles = (t as Record<string, unknown>).settingRoles as Record<string, unknown> | undefined;
  const i18n = (settingRoles?.editUsers as Record<string, string>) || {};

  // Get language-aware role name
  const roleName = language === "ar" ? (role.nameAr || role.nameEn) : role.nameEn;
  const roleId = role.id;
  const [selectedUsers, setSelectedUsers] = useState<
    MultiValue<UserOptionType>
  >([]);
  const [isLoading, setIsLoading] = useState(false);

  // Store original user IDs for comparison/reset
  const originalUserIds = useRef<string[]>([]);

  // Options derived from pre-loaded users
  const userOptions: UserOptionType[] = useMemo(
    () =>
      preloadedUsers.map((u) => ({
        value: u.id, // Use user ID (UUID) as unique identifier
        label: u.username,
        username: u.username,
        email: u.email,
      })),
    [preloadedUsers]
  );

  /* ------------------------------------------------------------------
   * Single effect: fetch role users + initialise selection on open
   * -----------------------------------------------------------------*/
  useEffect(() => {
    const fetchAndInit = async () => {
      if (!roleId || !open) {return;}

      setIsLoading(true);
      try {
        const users = await fetchRoleUsers(roleId);

        const initialSelected = userOptions.filter((opt) =>
          users.some((u) => u.id === opt.value)
        );
        setSelectedUsers(initialSelected);
        originalUserIds.current = initialSelected.map((u) => u.value);
      } catch (error) {
        // Log technical error to console only
        console.error("Failed to load role users:", error);
        // Show user-friendly error message
        toast.error(i18n.loadUsersError || "Failed to load role users");
      } finally {
        setIsLoading(false);
      }
    };

    fetchAndInit();
     
  }, [roleId, open, userOptions]); // i18n string not needed in deps

  // Change detection
  const hasChanges = useMemo(() => {
    const curr = selectedUsers.map((u) => u.value).sort();
    const orig = [...originalUserIds.current].sort();
    return (
      curr.length !== orig.length || curr.some((_id, idx) => _id !== orig[idx])
    );
  }, [selectedUsers]);

  /* ------------------------------------------------------------------
   * Save & cancel handlers
   * -----------------------------------------------------------------*/
  const performSave = async () => {
    setIsLoading(true);
    try {
      const updatedIds = selectedUsers.map((u) => u.value);
      await updateRoleUsers(roleId, updatedIds);

      toast.success(i18n.updateSuccess || "Role users updated successfully");
      if (onMutate) {onMutate();}
      if (onSuccess) {onSuccess();}
      onOpenChange(false);
    } catch (error) {
      // Log technical error to console only
      console.error("Failed to update role users:", error);
      // Show user-friendly error message
      toast.error(i18n.updateError || "Failed to update role users");
    } finally {
      setIsLoading(false);
    }
  };

  /* ------------------------------------------------------------------
   * Confirmation dialog
   * -----------------------------------------------------------------*/
  const {
    isOpen: confirmOpen,
    isLoading: confirmLoading,
    open: openConfirmDialog,
    close: closeConfirmDialog,
    confirm: confirmSave,
    confirmLabel,
    cancelLabel,
  } = useConfirmationDialog(performSave);

  const handleSave = () => {
    if (!hasChanges) {return;}
    openConfirmDialog();
  };

  const handleCancel = () => {
    const reset = userOptions.filter((o) =>
      originalUserIds.current.includes(o.value)
    );
    setSelectedUsers(reset);
    onOpenChange(false);
  };

  return (
    <>
      <Sheet open={open} onOpenChange={handleCancel}>
        <SheetContent
          className="w-full sm:max-w-xl"
          side="right"
        >
          <SheetHeader>
            <SheetTitle className={`flex items-center gap-3 ${isRTL ? 'flex-row-reverse' : ''}`}>
              <Users className="h-5 w-5" />
              {i18n.title || "Edit Role Users"}
            </SheetTitle>
            <SheetDescription>
              {((i18n.description || "Manage users assigned to") + " " + roleName)}
            </SheetDescription>
          </SheetHeader>

          <div className="py-6">
            <div className="space-y-2">
              <Label className="text-sm">
                {i18n.assignedUsers || "Assigned Users"}{" "}
                {(i18n.selectedCount || "({count} selected)").replace(
                  "{count}",
                  selectedUsers.length.toString()
                )}
              </Label>

              {isLoading ? (
                <div className="flex items-center justify-center h-[120px] border">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                <Select<UserOptionType, true>
                  instanceId="role-users-select"
                  options={userOptions}
                  isMulti
                  isSearchable
                  onChange={setSelectedUsers}
                  value={selectedUsers}
                  placeholder={i18n.searchPlaceholder || "Search users..."}
                  className="react-select-container"
                  classNamePrefix="react-select"
                  components={{ Option: CustomUserOption }}
                  isDisabled={isLoading}
                  maxMenuHeight={200}
                  noOptionsMessage={({ inputValue }) =>
                    inputValue
                      ? (i18n.noUsersFound || 'No users found matching "{searchTerm}"').replace("{searchTerm}", inputValue)
                      : (i18n.noUsersAvailable || "No users available")
                  }
                  filterOption={(option, inputVal) => {
                    if (!inputVal) {return true;}
                    const term = inputVal.toLowerCase();
                    return (
                      option.label.toLowerCase().includes(term) ||
                      (option.data?.email?.toLowerCase() ?? "").includes(term)
                    );
                  }}
                />
              )}
            </div>
          </div>

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
                onClick={handleSave}
                disabled={!hasChanges || isLoading}
                className="flex-1 sm:flex-none min-w-[120px] h-10 rounded-none"
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin me-2" />}
                {isLoading ? (i18n.saving || "Saving...") : (i18n.saveChanges || "Save Changes")}
              </Button>
            </div>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      <ConfirmationDialog
        open={confirmOpen}
        onOpenChange={closeConfirmDialog}
        onConfirm={confirmSave}
        isLoading={confirmLoading}
        title={i18n.confirmTitle || "Update Role Users"}
        description={i18n.confirmDescription || "Are you sure you want to update the users for this role?"}
        confirmText={confirmLabel}
        cancelText={cancelLabel}
      />
    </>
  );
}
