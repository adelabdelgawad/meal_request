
"use client";

import React, { useState, useEffect } from 'react';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  VisibilityState,
  RowSelectionState,
  ColumnSizingState,
  Table as TanStackTable,
} from '@tanstack/react-table';
import { Loader2 } from 'lucide-react';
import { useLanguage, translate } from '@/hooks/use-language';

interface DataTableProps<TData> {
  _data: TData[];
  columns: ColumnDef<TData>[];
  onRowSelectionChange?: (selectedRows: TData[]) => void;
  renderToolbar?: (table: TanStackTable<TData>) => React.ReactNode;
  _isLoading?: boolean;
  tableInstanceHook?: (tableInstance: TanStackTable<TData>) => void;
  enableRowSelection?: boolean;
  enableSorting?: boolean;
  getRowClassName?: (row: TData) => string;
  renderMobileCard?: (item: TData, index: number) => React.ReactNode;
}

export function DataTable<TData>({
  _data,
  columns,
  onRowSelectionChange,
  renderToolbar,
  _isLoading = false,
  tableInstanceHook,
  enableRowSelection = true,
  enableSorting = true,
  getRowClassName,
  renderMobileCard,
}: DataTableProps<TData>) {
  const { t } = useLanguage();
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});

  const table = useReactTable<TData>({
    data: (_data || []) as TData[],
    columns,
    getCoreRowModel: getCoreRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onColumnSizingChange: setColumnSizing,
    state: {
      columnVisibility,
      rowSelection,
      columnSizing,
    },
    enableRowSelection,
    enableSorting,
    enableColumnResizing: true,
    columnResizeMode: 'onChange',
  });

  useEffect(() => {
    if (onRowSelectionChange) {
      const selectedRows = table.getFilteredSelectedRowModel().rows.map(
        (row) => row.original
      );
      onRowSelectionChange(selectedRows);
    }
  }, [rowSelection, onRowSelectionChange, table]);

  useEffect(() => {
    if (tableInstanceHook) {
      tableInstanceHook(table);
    }
  }, [table, tableInstanceHook]);

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).__resetTableSelection = () => {
      setRowSelection({});
    };
    return () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (window as any).__resetTableSelection;
    };
  }, []);

  return (
    <div className="flex flex-col h-full">
      {renderToolbar && renderToolbar(table)}

      {/* Mobile Card View - visible on small screens */}
      {renderMobileCard && (
        <div className="md:hidden">
          {_isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">{translate(t, 'common.loading') || 'Loading...'}</p>
            </div>
          ) : _data && _data.length > 0 ? (
            <div className="space-y-3 p-2">
              {_data.map((item, index) => (
                <div key={index}>
                  {renderMobileCard(item, index)}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              {translate(t, 'table.noDataAvailable') || 'No data available'}
            </div>
          )}
        </div>
      )}

      {/* Desktop Table View - hidden on small screens when mobile cards available */}
      <div className={`bg-card relative border-x border-border overflow-y-auto flex-1 min-h-0 ${renderMobileCard ? 'hidden md:block' : ''}`}>
        {_isLoading && (
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-20">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">{translate(t, 'table.noDataAvailable') || 'Loading data...'}</p>
            </div>
          </div>
        )}

        <table className="w-full text-sm table-auto">
          <thead className="bg-background border-b border-border sticky top-0 z-10">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const minSize = header.column.columnDef.minSize ?? 50;
                  const maxSize = header.column.columnDef.maxSize ?? 500;

                  return (
                    <th
                      key={header.id}
                      className="px-4 py-2 text-center align-middle font-semibold text-foreground relative border-r border-border"
                      style={{
                        width: header.getSize(),
                        minWidth: minSize,
                        maxWidth: maxSize,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                      {header.column.getCanResize() && (
                        <div
                          onMouseDown={header.getResizeHandler()}
                          onTouchStart={header.getResizeHandler()}
                          className="absolute top-0 right-0 h-full w-1 cursor-col-resize select-none touch-none group"
                          style={{
                            userSelect: 'none',
                          }}
                        >
                          <div className="h-full w-full group-hover:bg-primary transition-colors" />
                        </div>
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className="bg-card divide-y divide-border">
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => {
                const isSelected = row.getIsSelected();
                const customRowClass = getRowClassName ? getRowClassName(row.original) : '';
                return (
                  <tr
                    key={row.id}
                    className={`transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-accent hover:bg-accent/80'
                        : 'hover:bg-muted/50'
                    } ${_isLoading ? 'opacity-50' : ''} ${customRowClass}`}
                    onClick={(e) => {
                      if (_isLoading) {return;}
                      const target = e.target as HTMLElement;
                      if (target.closest('input[type="checkbox"]')) {
                        return;
                      }
                      row.toggleSelected();
                    }}
                  >
                    {row.getVisibleCells().map((cell) => {
                      const minSize = cell.column.columnDef.minSize ?? 50;
                      const maxSize = cell.column.columnDef.maxSize ?? 500;

                      return (
                        <td
                          key={cell.id}
                          className="px-4 py-3 text-center align-middle text-foreground truncate"
                          style={{
                            width: cell.column.getSize(),
                            minWidth: minSize,
                            maxWidth: maxSize,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext()
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            ) : (
              <tr>
                <td
                  colSpan={columns.length}
                  className="text-center py-12 text-muted-foreground"
                >
                  {_isLoading ? (
                    <div className="flex flex-col items-center gap-2">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      <span>{translate(t, 'common.loading') || 'Loading...'}</span>
                    </div>
                  ) : (
                    translate(t, 'table.noDataAvailable') || 'No data available'
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
