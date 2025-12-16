"use client";

import React from "react";
import { Button } from "@/components/data-table";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import { Check } from "lucide-react";
import { useLanguage, translate } from "@/hooks/use-language";

interface EnableButtonProps {
  selectedIds: (string | number)[];
  onEnable: (ids: (string | number)[]) => void;
  disabled?: boolean;
  itemName?: string;
}

export const EnableButton: React.FC<EnableButtonProps> = ({
  selectedIds,
  onEnable,
  disabled = false,
  itemName = "users",
}) => {
  const { t } = useLanguage();
  const hasSelection = selectedIds.length > 0;
  const count = selectedIds.length;
  const itemLabel = count === 1 ? "user" : itemName;

  const {
    isOpen,
    isLoading,
    open,
    close,
    confirm,
  } = useConfirmationDialog(() => onEnable(selectedIds));

  return (
    <>
      <Button
        onClick={open}
        disabled={!hasSelection || disabled}
        variant="success"
        size="default"
        icon={<Check className="w-4 h-4" />}
        tooltip={translate(t, 'table.bulk.enableTooltip').replace('{items}', itemName)}
      >
        {translate(t, 'table.bulk.enable')}
      </Button>

      <ConfirmationDialog
        open={isOpen}
        onOpenChange={close}
        onConfirm={confirm}
        isLoading={isLoading}
        title={translate(t, 'table.bulk.enableTitle').replace('{items}', itemName)}
        description={translate(t, 'table.bulk.enableMessage')
          .replace('{count}', String(count))
          .replace('{item}', itemLabel)}
        confirmText={translate(t, 'table.dialog.confirm')}
        cancelText={translate(t, 'table.dialog.cancel')}
        variant="default"
      />
    </>
  );
};
