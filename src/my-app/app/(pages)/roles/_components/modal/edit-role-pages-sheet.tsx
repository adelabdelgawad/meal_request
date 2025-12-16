
"use client";

import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { toast } from "@/components/ui/custom-toast";
import { Label } from "@/components/ui/label";
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
import { getRolePages, updateRolePages } from "@/lib/api/roles";
import { Loader2, Save, FileText, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import Select, { MultiValue, components, type OptionProps } from 'react-select';
import type { RoleResponse } from "@/types/roles";
import type { PageResponse } from "@/types/pages";

interface EditRolePagesSheetProps {
  role: RoleResponse;
  preloadedPages: PageResponse[];
  onMutate?: () => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type PageOptionType = {
  value: number;
  label: string;
  description?: string;
};

// Custom Option component
const CustomPageOption = (props: OptionProps<PageOptionType, true>) => (
  <components.Option {...props}>
    <div>
      <div className="font-medium">{props.data.label}</div>
      {props.data.description && (
        <div className="text-sm text-muted-foreground">
          {props.data.description}
        </div>
      )}
    </div>
  </components.Option>
);

export function EditRolePagesSheet({
  role,
  preloadedPages,
  onMutate,
  open,
  onOpenChange,
}: EditRolePagesSheetProps) {
  const { t, language } = useLanguage();
  const isRTL = language === "ar";
  const settingRoles = (t as Record<string, unknown>).settingRoles as Record<string, unknown> | undefined;
  const i18n = (settingRoles?.editPages as Record<string, string>) || {};
  const messages = (settingRoles?.messages as Record<string, string>) || {};

  // Get language-aware role name
  const roleName = language === "ar" ? (role.nameAr || role.nameEn) : role.nameEn;

  const [_isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);
  const [originalPageIds, setOriginalPageIds] = useState<number[]>([]);
  const [selectedPageIds, setSelectedPageIds] = useState<number[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const selectRef = useRef<any>(null);

  // Fetch role pages on mount
  useEffect(() => {
    if (!open) {
      // Reset state when closing
      setOriginalPageIds([]);
      setSelectedPageIds([]);
      setIsFetching(true);
      return;
    }

    const fetchRolePages = async () => {
      setIsFetching(true);
      try {
        const pages = await getRolePages(role.id, true);
        const pageIds = pages.map((page: PageResponse) => page.id);
        setOriginalPageIds(pageIds);
        setSelectedPageIds(pageIds);
      } catch (error) {
        // Log technical error to console only
        console.error("Failed to load role pages:", error);
        // Show user-friendly error message
        toast.error(messages.pagesError || "Failed to load role pages");
      } finally {
        setIsFetching(false);
      }
    };

    fetchRolePages();
  }, [role.id, open, messages.pagesError]);

  // Convert pages to options with language-aware labels
  const pageOptions: PageOptionType[] = useMemo(
    () =>
      preloadedPages
        .map((page) => ({
          value: page.id,
          label: language === "ar" ? (page.nameAr || page.nameEn) : page.nameEn,
          description: language === "ar"
            ? (page.descriptionAr || page.descriptionEn || undefined)
            : (page.descriptionEn || page.descriptionAr || undefined),
        })),
    [preloadedPages, language]
  );

  // Convert selected page IDs to selected options
  const selectedOptions = useMemo(
    () => pageOptions.filter((option) => selectedPageIds.includes(option.value)),
    [pageOptions, selectedPageIds]
  );

  // Handle selection change
  const handleSelectionChange = (newValue: MultiValue<PageOptionType>) => {
    setSelectedPageIds(newValue.map((option) => option.value));
  };

  // Check if there are changes
  const hasChanges = useMemo(() => {
    if (selectedPageIds.length !== originalPageIds.length) {return true;}
    return !selectedPageIds.every((_id) => originalPageIds.includes(_id));
  }, [selectedPageIds, originalPageIds]);

  // Perform save
  const performSave = async () => {
    setIsLoading(true);
    try {
      await updateRolePages(role.id, selectedPageIds);
      toast.success(messages.pagesUpdated || "Role pages updated successfully");
      if (onMutate) {onMutate();}
      onOpenChange(false);
    } catch (error) {
      // Log technical error to console only
      console.error("Failed to update role pages:", error);
      // Show user-friendly error message
      toast.error(messages.pagesError || "Failed to update role pages");
    } finally {
      setIsLoading(false);
    }
  };

  // Confirmation dialog
  const {
    isOpen: showConfirmDialog,
    isLoading: confirmLoading,
    open: openConfirmDialog,
    close: closeConfirmDialog,
    confirm: confirmSave,
    confirmLabel,
    cancelLabel,
  } = useConfirmationDialog(performSave);

  const handleSaveClick = () => {
    if (!hasChanges) {
      onOpenChange(false);
      return;
    }
    openConfirmDialog();
  };

  const handleCancel = () => {
    setSelectedPageIds(originalPageIds);
    onOpenChange(false);
  };

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent
          className="w-full sm:max-w-lg overflow-y-auto"
          side="right"
        >
          <SheetHeader>
            <SheetTitle className={`flex items-center gap-3 ${isRTL ? 'flex-row-reverse' : ''}`}>
              <FileText className="h-5 w-5" />
              {i18n.title || "Edit Role Pages"}
            </SheetTitle>
            <SheetDescription>
              {((i18n.description || "Manage pages assigned to") + " " + roleName)}
            </SheetDescription>
          </SheetHeader>

          {isFetching ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>{(i18n.selectPages || "Select Pages")} ({selectedPageIds.length} {i18n.selected || "selected"})</Label>
                <Select
                  ref={selectRef}
                  isMulti
                  value={selectedOptions}
                  onChange={handleSelectionChange}
                  options={pageOptions}
                  components={{ Option: CustomPageOption }}
                  placeholder={i18n.searchPlaceholder || "Search pages..."}
                  className="react-select-container"
                  classNamePrefix="react-select"
                  isDisabled={_isLoading}
                  menuPortalTarget={typeof document !== 'undefined' ? document.body : null}
                  styles={{
                    menuPortal: (base) => ({ ...base, zIndex: 9999 }),
                  }}
                />
              </div>
            </div>
          )}

          <SheetFooter>
            <div className="flex flex-col-reverse sm:flex-row gap-3 w-full">
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
                disabled={_isLoading || isFetching}
                className="flex-1 sm:flex-none min-w-[120px] h-10 rounded-none"
              >
                <X className="h-4 w-4 me-2" />
                {i18n.cancel || "Cancel"}
              </Button>
              <Button
                type="button"
                onClick={handleSaveClick}
                disabled={_isLoading || isFetching || !hasChanges}
                className="flex-1 sm:flex-none min-w-[120px] h-10 rounded-none"
              >
                {_isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin me-2" />
                    {i18n.saving || "Saving..."}
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 me-2" />
                    {i18n.save || "Save Changes"}
                  </>
                )}
              </Button>
            </div>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      <ConfirmationDialog
        open={showConfirmDialog}
        onOpenChange={closeConfirmDialog}
        onConfirm={confirmSave}
        isLoading={confirmLoading}
        title={i18n.confirmTitle || "Update Role Pages"}
        description={((i18n.confirmMessage || 'Are you sure you want to update the pages for "{roleName}"?')).replace("{roleName}", roleName)}
        confirmText={confirmLabel}
        cancelText={cancelLabel}
      />
    </>
  );
}
