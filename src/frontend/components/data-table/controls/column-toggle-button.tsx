"use client";

import { Menu } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "../ui/button";
import { Table } from "@tanstack/react-table";
import { useLanguage, translate } from "@/hooks/use-language";

interface ColumnToggleButtonProps<TData> {
  table: Table<TData> | null;
  /** Optional map of column IDs to translated labels */
  columnLabels?: Record<string, string>;
}

// Helper function to convert columnId like "enName" to "EN Name"
function prettifyColumnName(columnId: string): string {
  // Remove leading 'Is' or 'is'
  const withoutIs = columnId.replace(/^is/i, "");

  // Insert spaces before capital letters
  const spaced = withoutIs.replace(/([A-Z])/g, " $1").trim();

  // Capitalize words, but fully uppercase if word length < 3
  const words = spaced.split(" ").map((word) => {
    return word.length < 3
      ? word.toUpperCase()
      : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
  });

  return words.join(" ");
}

/**
 * Get display name for a column, with priority:
 * 1. columnLabels prop (explicit translations)
 * 2. column.columnDef.meta?.label (from column definition)
 * 3. prettifyColumnName fallback
 */
function getColumnDisplayName(
  column: { id: string; columnDef: { meta?: { label?: string } } },
  columnLabels?: Record<string, string>
): string {
  // Priority 1: Explicit label from props
  if (columnLabels?.[column.id]) {
    return columnLabels[column.id];
  }

  // Priority 2: Label from column meta
  if (column.columnDef.meta?.label) {
    return column.columnDef.meta.label;
  }

  // Priority 3: Prettify the column ID
  return prettifyColumnName(column.id);
}

export function ColumnToggleButton<TData>({ table, columnLabels }: ColumnToggleButtonProps<TData>) {
  const { t } = useLanguage();
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState(
    () => table?.getState().columnVisibility || {}
  );

  // Sync with table state whenever it changes
  useEffect(() => {
    if (!table) {return;}

    const updateVisibility = () => {
      setColumnVisibility({ ...table.getState().columnVisibility });
    };

    // Update immediately
    updateVisibility();

    // Set up a listener - using a small interval as fallback
    const interval = setInterval(updateVisibility, 100);

    return () => clearInterval(interval);
  }, [table, showColumnMenu]); // Re-run when menu opens

  const handleToggleMenu = () => {
    // Do nothing if table is not ready
    if (!table) {return;}
    setShowColumnMenu(!showColumnMenu);
  };

  return (
    <div className="relative">
      <Button
        onClick={handleToggleMenu}
        size="default"
        icon={<Menu className="w-4 h-4" />}
        tooltip={translate(t, 'table.columnsTooltip')}
      >
        {translate(t, 'table.columns')}
      </Button>

      {showColumnMenu && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowColumnMenu(false)}
          />
          <div className="absolute end-0 mt-2 me-1 w-56 bg-card border border-border shadow-lg z-20">
            <div className="p-2">
              <div className="text-xs font-semibold text-muted-foreground px-2 py-1 mb-1">
                {translate(t, 'table.toggleColumns')}
              </div>
              {table
                ?.getAllColumns()
                .filter((column) => column.getCanHide())
                .map((column) => {
                  const isVisible = columnVisibility[column.id] !== false;

                  return (
                    <label
                      key={column.id}
                      className="flex items-center gap-2 px-2 py-2 hover:bg-muted cursor-pointer text-foreground"
                    >
                      <input
                        type="checkbox"
                        checked={isVisible}
                        onChange={(e) => {
                          column.toggleVisibility(e.target.checked);
                          setColumnVisibility({
                            ...table.getState().columnVisibility,
                          });
                        }}
                        className="border-border"
                      />
                      <span className="text-sm">
                        {getColumnDisplayName(column, columnLabels)}
                      </span>
                    </label>
                  );
                })}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
