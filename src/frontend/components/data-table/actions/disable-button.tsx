"use client";

import React from "react";
import { Button } from "@/components/data-table";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import { Ban } from "lucide-react";
import { useLanguage, translate } from "@/hooks/use-language";

interface DisableButtonProps {
  selectedIds: (string | number)[];
  onDisable: (ids: (string | number)[]) => void;
  disabled?: boolean;
  itemName?: string;
}

export const DisableButton: React.FC<DisableButtonProps> = ({
  selectedIds,
  onDisable,
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
  } = useConfirmationDialog(() => onDisable(selectedIds));

  return (
    <>
      <Button
        onClick={open}
        disabled={!hasSelection || disabled}
        variant="danger"
        size="default"
        icon={<Ban className="w-4 h-4" />}
        tooltip={translate(t, 'table.bulk.disableTooltip').replace('{items}', itemName)}
      >
        {translate(t, 'table.bulk.disable')}
      </Button>

      <ConfirmationDialog
        open={isOpen}
        onOpenChange={close}
        onConfirm={confirm}
        isLoading={isLoading}
        title={translate(t, 'table.bulk.disableTitle').replace('{items}', itemName)}
        description={translate(t, 'table.bulk.disableMessage')
          .replace('{count}', String(count))
          .replace('{item}', itemLabel)}
        confirmText={translate(t, 'table.dialog.confirm')}
        cancelText={translate(t, 'table.dialog.cancel')}
        variant="destructive"
      />
    </>
  );
};
