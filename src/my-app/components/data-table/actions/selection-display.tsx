"use client";

import React from "react";
import { useLanguage, translate } from "@/hooks/use-language";

interface SelectionDisplayProps {
  selectedCount: number;
  onClearSelection: () => void;
  itemName?: string;
}

export const SelectionDisplay: React.FC<SelectionDisplayProps> = ({
  selectedCount,
  onClearSelection,
  itemName = "item",
}) => {
  const { t } = useLanguage();
  const hasSelection = selectedCount > 0;

  // Get translated item name if it matches known keys
  const getTranslatedItemName = () => {
    if (itemName === "user" || itemName === "users") {
      return selectedCount === 1
        ? translate(t, 'statusPanel.user')
        : translate(t, 'statusPanel.users');
    }
    if (itemName === "role" || itemName === "roles") {
      return selectedCount === 1
        ? translate(t, 'statusPanel.role')
        : translate(t, 'statusPanel.roles');
    }
    return itemName;
  };

  const getSelectionText = () => {
    if (hasSelection) {
      return translate(t, 'table.selection.selected')
        .replace('{count}', String(selectedCount))
        .replace('{item}', getTranslatedItemName());
    }
    return translate(t, 'table.selection.selectToPerform')
      .replace('{items}', itemName === "user" ? translate(t, 'statusPanel.users') : itemName + 's');
  };

  return (
    <div className="flex items-center gap-2">
      <span
        className={`text-sm font-medium ${
          hasSelection ? "text-foreground" : "text-muted-foreground"
        }`}
      >
        {getSelectionText()}
      </span>
      {hasSelection && (
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onClearSelection();
          }}
          className="p-1 hover:bg-muted transition-colors"
          title={translate(t, 'table.selection.clearSelection')}
        >
          <svg
            className="w-4 h-4 text-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
};
