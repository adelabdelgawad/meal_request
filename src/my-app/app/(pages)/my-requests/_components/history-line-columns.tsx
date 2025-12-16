'use client';

import { ColumnDef } from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import { Trash2, CheckCircle, XCircle } from 'lucide-react';
import type { RequestLine } from '@/types/meal-request.types';

interface ColumnTranslations {
  rowNum?: string;
  code?: string;
  employeeName?: string;
  title?: string;
  department?: string;
  shift?: string;
  status?: string;
  notes?: string;
  actions?: string;
  deleteLine?: string;
}

export function createHistoryLineColumns(
  locale: string,
  translations: ColumnTranslations,
  isPending: boolean,
  isDeletingLine: boolean,
  onDeleteLine: (line: RequestLine) => void
): ColumnDef<RequestLine>[] {
  const columns: ColumnDef<RequestLine>[] = [
    {
      id: 'rowNum',
      header: translations.rowNum || '#',
      size: 50,
      minSize: 40,
      maxSize: 60,
      cell: ({ row }) => (
        <div className="font-medium text-muted-foreground">{row.index + 1}</div>
      ),
    },
    {
      id: 'code',
      accessorKey: 'code',
      header: translations.code || 'Code',
      size: 80,
      minSize: 60,
      maxSize: 100,
      cell: ({ row }) => (
        <div className="font-mono text-sm">{row.original.code}</div>
      ),
    },
    {
      id: 'employeeName',
      header: translations.employeeName || 'Employee Name',
      size: 200,
      minSize: 150,
      maxSize: 300,
      cell: ({ row }) => {
        const localizedName = locale === 'ar' ? row.original.nameAr : row.original.nameEn;
        return <div className="font-medium truncate">{localizedName}</div>;
      },
    },
    {
      id: 'title',
      accessorKey: 'title',
      header: translations.title || 'Title',
      size: 150,
      minSize: 100,
      maxSize: 200,
      cell: ({ row }) => (
        <div className="text-muted-foreground truncate">{row.original.title || '-'}</div>
      ),
    },
    {
      id: 'department',
      header: translations.department || 'Department',
      size: 150,
      minSize: 100,
      maxSize: 250,
      cell: ({ row }) => {
        const localizedDept = locale === 'ar' ? row.original.departmentAr : row.original.departmentEn;
        return <div className="text-muted-foreground truncate">{localizedDept || '-'}</div>;
      },
    },
    {
      id: 'shift',
      accessorKey: 'shiftHours',
      header: translations.shift || 'Shift',
      size: 70,
      minSize: 60,
      maxSize: 100,
      cell: ({ row }) => (
        <div>{row.original.shiftHours ? `${row.original.shiftHours}h` : '-'}</div>
      ),
    },
    {
      id: 'status',
      header: translations.status || 'Status',
      size: 100,
      minSize: 80,
      maxSize: 120,
      cell: ({ row }) => (
        <div className="flex items-center justify-center">
          {row.original.accepted ? (
            <CheckCircle className="h-5 w-5 text-green-500" />
          ) : (
            <XCircle className="h-5 w-5 text-red-500" />
          )}
        </div>
      ),
    },
    {
      id: 'notes',
      header: translations.notes || 'Notes',
      size: 200,
      minSize: 150,
      maxSize: 300,
      cell: ({ row }) => (
        <div className="text-muted-foreground text-sm truncate">{row.original.notes || '-'}</div>
      ),
    },
  ];

  // Add actions column only if request is pending
  if (isPending) {
    columns.push({
      id: 'actions',
      header: translations.actions || 'Actions',
      size: 80,
      minSize: 70,
      maxSize: 100,
      cell: ({ row }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 cursor-pointer"
            onClick={() => onDeleteLine(row.original)}
            disabled={isDeletingLine}
            title={translations.deleteLine || 'Delete Line'}
          >
            <Trash2 className="h-4 w-4 text-red-600 dark:text-red-400" />
            <span className="sr-only">{translations.deleteLine || 'Delete Line'}</span>
          </Button>
        </div>
      ),
    });
  }

  return columns;
}
