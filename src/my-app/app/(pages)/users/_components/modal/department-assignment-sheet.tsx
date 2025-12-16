"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
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
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Building2, Loader2, Save, X, AlertCircle, Info, CheckSquare, XSquare, Search } from "lucide-react";
import { toast } from "@/components/ui/custom-toast";
import { useLanguage } from "@/hooks/use-language";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import {
  getUserDepartments,
  updateUserDepartments,
} from "@/lib/api/user-departments";
import type { UserWithRolesResponse } from "@/types/users";
import type { DepartmentForAssignment } from "@/lib/actions/departments.actions";

interface DepartmentAssignmentSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: UserWithRolesResponse;
  departments: DepartmentForAssignment[];
  onSuccess: () => void;
}

export function DepartmentAssignmentSheet({
  open,
  onOpenChange,
  user,
  departments,
  onSuccess,
}: DepartmentAssignmentSheetProps) {
  const { t, language } = useLanguage();
  const isRTL = language === "ar";

  // Translation helpers
  const usersT = (t as Record<string, unknown>).users as
    | Record<string, unknown>
    | undefined;
  const i18n = {
    departments: (usersT?.departments as Record<string, unknown>) || {},
    toast: (usersT?.toast as Record<string, unknown>) || {},
    columns: (usersT?.columns as Record<string, unknown>) || {},
  };

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const initialSelectedIds = useRef<Set<number>>(new Set());

  // Sort and filter departments: selected first, then filter by search query
  const sortedAndFilteredDepartments = useMemo(() => {
    const getDeptName = (dept: DepartmentForAssignment) =>
      language === "ar" ? dept.nameAr : dept.nameEn;

    // Filter by search query
    const filtered = searchQuery
      ? departments.filter((dept) =>
          getDeptName(dept).toLowerCase().includes(searchQuery.toLowerCase())
        )
      : departments;

    // Sort: selected first, then alphabetically
    return [...filtered].sort((a, b) => {
      const aSelected = selectedIds.has(a.id);
      const bSelected = selectedIds.has(b.id);
      if (aSelected && !bSelected) return -1;
      if (!aSelected && bSelected) return 1;
      return getDeptName(a).localeCompare(getDeptName(b));
    });
  }, [departments, selectedIds, searchQuery, language]);

  const closeSheet = () => {
    setSelectedIds(new Set());
    setIsDirty(false);
    setIsMounted(false);
    setError(null);
    setSearchQuery("");
    onOpenChange(false);
  };

  const performSave = async () => {
    setIsLoading(true);

    try {
      await updateUserDepartments(user.id, Array.from(selectedIds));

      toast.success(
        (i18n.toast.departmentsUpdated as string) ||
          "Department assignments updated"
      );
      setIsDirty(false);
      onOpenChange(false);
      onSuccess();
    } catch (error) {
      console.error("Failed to update department assignments:", error);
      toast.error(
        (i18n.toast.departmentsUpdateFailed as string) ||
          "Failed to update department assignments"
      );
      throw error;
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

  // Fetch user's assigned department IDs when sheet opens
  // (departments list is already loaded from server)
  useEffect(() => {
    if (open && user) {
      setIsMounted(true);
      setIsFetching(true);
      setError(null);

      getUserDepartments(user.id)
        .then((data) => {
          const assignedIds = new Set(data.departmentIds);
          setSelectedIds(assignedIds);
          initialSelectedIds.current = new Set(assignedIds);
          setIsDirty(false);
        })
        .catch((err) => {
          console.error("Failed to fetch user departments:", err);
          setError(
            (i18n.departments?.fetchError as string) ||
              "Failed to load user department assignments"
          );
        })
        .finally(() => {
          setIsFetching(false);
        });
    }
  }, [open, user, i18n.departments?.fetchError]);

  // Check if dirty
  useEffect(() => {
    if (!isMounted) return;

    const currentIds = Array.from(selectedIds).sort();
    const initialIds = Array.from(initialSelectedIds.current).sort();

    const dirty =
      currentIds.length !== initialIds.length ||
      !currentIds.every((id, idx) => id === initialIds[idx]);

    setIsDirty(dirty);
  }, [selectedIds, isMounted]);

  const handleToggle = (departmentId: number, checked: boolean) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(departmentId);
      } else {
        newSet.delete(departmentId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    const allIds = new Set(departments.map((d) => d.id));
    setSelectedIds(allIds);
  };

  const handleClearAll = () => {
    setSelectedIds(new Set());
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

  const getDepartmentName = (dept: DepartmentForAssignment): string => {
    return language === "ar" ? dept.nameAr : dept.nameEn;
  };

  if (!isMounted) {
    return null;
  }

  return (
    <>
      <Sheet open={open} onOpenChange={handleClose}>
        <SheetContent
          className="w-full sm:max-w-lg flex flex-col overflow-hidden"
          id="department-assignment-sheet"
          side="right"
        >
          <SheetHeader className="shrink-0">
            <SheetTitle
              className={`flex items-center gap-2 ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <Building2 className="h-5 w-5 shrink-0" />
              <span>{(i18n.departments.title as string) || "Department Assignments"}</span>
            </SheetTitle>
            <SheetDescription className={isRTL ? "text-right" : ""}>
              {(i18n.departments.description as string) ||
                "Manage department visibility for"}{" "}
              {user.username}
            </SheetDescription>
          </SheetHeader>

          {/* Info Banner */}
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md">
            <div
              className={`flex gap-2 ${isRTL ? "flex-row-reverse" : ""}`}
            >
              <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-blue-700 dark:text-blue-300">
                {(i18n.departments.infoText as string) ||
                  "When no departments are selected, the user can see meal requests from ALL departments. Select specific departments to restrict visibility."}
              </p>
            </div>
          </div>

          {/* User Info Display */}
          <div className="grid grid-cols-1 gap-4 border p-4 bg-muted/50 text-sm sm:grid-cols-2 mt-6">
            <div>
              <Label className="text-muted-foreground">
                {(i18n.columns.username as string) || "Username"}
              </Label>
              <div>{user.username}</div>
            </div>
            <div>
              <Label className="text-muted-foreground">
                {(i18n.departments.assignedCount as string) || "Assigned"}
              </Label>
              <div>
                {selectedIds.size === 0 ? (
                  <span className="text-green-600 dark:text-green-400">
                    {(i18n.departments.allDepartments as string) ||
                      "All departments"}
                  </span>
                ) : (
                  `${selectedIds.size} ${
                    (i18n.departments.departmentsLabel as string) ||
                    "departments"
                  }`
                )}
              </div>
            </div>
          </div>

          {/* Error State */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-md">
              <div
                className={`flex gap-2 ${isRTL ? "flex-row-reverse" : ""}`}
              >
                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-red-700 dark:text-red-300">
                  {error}
                </p>
              </div>
            </div>
          )}

          {/* Loading State */}
          {isFetching && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Department List */}
          {!isFetching && !error && (
            <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0 space-y-4 mt-6">
              {/* Search and Quick Actions */}
              <div className="space-y-3 shrink-0">
                {/* Search Input */}
                <div className="relative">
                  <Search className={`absolute top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground ${isRTL ? "right-3" : "left-3"}`} />
                  <Input
                    type="text"
                    placeholder={(i18n.departments.searchPlaceholder as string) || "Search departments..."}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className={`${isRTL ? "pr-10 text-right" : "pl-10"}`}
                  />
                </div>

                {/* Quick Actions */}
                <div
                  className={`flex gap-2 ${
                    isRTL ? "flex-row-reverse justify-end" : "justify-start"
                  }`}
                >
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleClearAll}
                    disabled={isLoading}
                    className={`${isRTL ? "flex-row-reverse" : ""}`}
                  >
                    <XSquare className={`h-4 w-4 ${isRTL ? "ms-2" : "me-2"}`} />
                    {(i18n.departments.clearAll as string) || "Clear All"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleSelectAll}
                    disabled={isLoading}
                    className={`${isRTL ? "flex-row-reverse" : ""}`}
                  >
                    <CheckSquare className={`h-4 w-4 ${isRTL ? "ms-2" : "me-2"}`} />
                    {(i18n.departments.selectAll as string) || "Select All"}
                  </Button>
                </div>
              </div>

              {/* Department Switches */}
              <div className="flex-1 min-h-0 overflow-y-auto border rounded-md p-2">
                {sortedAndFilteredDepartments.length === 0 ? (
                  <p className="text-center text-muted-foreground py-4">
                    {searchQuery
                      ? ((i18n.departments.noResults as string) || "No departments found")
                      : ((i18n.departments.noDepartments as string) || "No departments available")}
                  </p>
                ) : (
                  sortedAndFilteredDepartments.map((dept) => (
                    <div
                      key={dept.id}
                      className={`flex items-center gap-4 px-3 py-2.5 hover:bg-muted/50 rounded-md transition-colors ${
                        isRTL ? "flex-row-reverse" : ""
                      }`}
                    >
                      <Label
                        htmlFor={`dept-${dept.id}`}
                        className="flex-1 cursor-pointer font-normal truncate"
                      >
                        {getDepartmentName(dept)}
                      </Label>
                      <Switch
                        id={`dept-${dept.id}`}
                        checked={selectedIds.has(dept.id)}
                        onCheckedChange={(checked) =>
                          handleToggle(dept.id, checked)
                        }
                        disabled={isLoading}
                        className="data-[state=checked]:bg-green-600 shrink-0"
                      />
                    </div>
                  ))
                )}
              </div>

              <SheetFooter className="pt-4 shrink-0">
                <div
                  className={`flex justify-between items-center w-full ${
                    isRTL ? "flex-row-reverse" : ""
                  }`}
                >
                  <div className="text-sm text-gray-500">
                    {isDirty &&
                      ((i18n.departments.unsavedChanges as string) ||
                        "Unsaved changes")}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleClose}
                      disabled={isLoading}
                    >
                      <X className="me-2 h-4 w-4" />
                      {(i18n.departments.cancel as string) || "Cancel"}
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
                      {(i18n.departments.save as string) || "Save"}
                    </Button>
                  </div>
                </div>
              </SheetFooter>
            </form>
          )}
        </SheetContent>
      </Sheet>

      {/* Close Confirmation Dialog */}
      <ConfirmationDialog
        open={showCloseConfirmDialog}
        onOpenChange={closeCloseDialog}
        onConfirm={handleCloseConfirm}
        isLoading={closeConfirmLoading}
        title={
          (i18n.departments.confirmCloseTitle as string) || "Confirm Close"
        }
        description={
          (i18n.departments.confirmCloseMessage as string) ||
          "You have unsaved changes. Are you sure you want to close?"
        }
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
        title={(i18n.departments.confirmSaveTitle as string) || "Confirm Save"}
        description={
          (i18n.departments.confirmSaveMessage as string) ||
          "Are you sure you want to save these department assignments?"
        }
        confirmText={saveConfirmLabel}
        cancelText={saveCancelLabel}
      />
    </>
  );
}
