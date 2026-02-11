'use client';

import { ColumnDef } from '@tanstack/react-table';
import { format } from 'date-fns';
import { Copy, Eye, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { MealRequest } from '@/types/meal-request.types';
import { StatusBadge } from '../../requests/_components/table/status-badge';

interface TableTranslations {
  id?: string;
  requestTime?: string;
  mealType?: string;
  totalRequests?: string;
  accepted?: string;
  status?: string;
  closedTime?: string;
  notes?: string;
  actions?: string;
  cannotCopyPending?: string;
  copyRequest?: string;
  viewDetails?: string;
  deleteRequest?: string;
  canOnlyDeletePending?: string;
}

interface Translations {
  myRequests?: { table?: TableTranslations };
  requests?: { table?: TableTranslations };
}

/**
 * Creates read-only columns for history requests table
 * Includes view, copy, and delete actions
 */
export function createHistoryColumns(
  t: Translations | null,
  locale: string,
  onView: (request: MealRequest) => void,
  onCopy: (request: MealRequest) => void,
  onDelete: (request: MealRequest) => void,
  isCopying: boolean = false,
  isDeleting: boolean = false
): ColumnDef<MealRequest>[] {
  // Get translations from the myRequests.table namespace, fallback to requests.table
  const table = t?.myRequests?.table || t?.requests?.table || {};

  return [
    {
      accessorKey: 'mealRequestId',
      header: table.id || '#',
      size: 80,
      cell: ({ row }) => (
        <div className="font-medium">{row.original.mealRequestId}</div>
      ),
    },
    {
      accessorKey: 'requestTime',
      header: table.requestTime || 'Request Time',
      size: 180,
      cell: ({ row }) => (
        <div className="text-sm">
          {format(new Date(row.original.requestTime), 'dd/MM/yyyy HH:mm:ss')}
        </div>
      ),
    },
    {
      id: 'mealType',
      accessorFn: (row) => locale === 'ar' ? row.mealTypeAr : row.mealTypeEn,
      header: table.mealType || 'Type',
      size: 120,
      cell: ({ row }) => {
        const localizedMealType = locale === 'ar' ? row.original.mealTypeAr : row.original.mealTypeEn;
        return <div className="truncate">{localizedMealType}</div>;
      },
    },
    {
      accessorKey: 'totalRequestLines',
      header: table.totalRequests || 'Requests',
      size: 100,
      cell: ({ row }) => (
        <div className="font-medium">{row.original.totalRequestLines}</div>
      ),
    },
    {
      accessorKey: 'acceptedRequestLines',
      header: table.accepted || 'Accepted',
      size: 100,
      cell: ({ row }) => (
        <div className="font-medium text-green-600 dark:text-green-400">
          {row.original.acceptedRequestLines ?? 0}
        </div>
      ),
    },
    {
      id: 'status',
      accessorFn: (row) => locale === 'ar' ? row.statusNameAr : row.statusNameEn,
      header: table.status || 'Status',
      size: 120,
      cell: ({ row }) => {
        const statusEn = row.original.statusNameEn;
        const localizedStatus = locale === 'ar' ? row.original.statusNameAr : row.original.statusNameEn;

        return <StatusBadge status={statusEn} label={localizedStatus} />;
      },
    },
    {
      accessorKey: 'closedTime',
      header: table.closedTime || 'Closed Time',
      size: 180,
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          {row.original.closedTime
            ? format(new Date(row.original.closedTime), 'dd/MM/yyyy HH:mm:ss')
            : '-'}
        </div>
      ),
    },
    {
      accessorKey: 'notes',
      header: table.notes || 'Notes',
      size: 200,
      cell: ({ row }) => (
        <div className="truncate text-muted-foreground" title={row.original.notes || ''}>
          {row.original.notes || '-'}
        </div>
      ),
    },
    {
      id: 'actions',
      header: table.actions || 'Actions',
      size: 150,
      cell: ({ row }) => {
        const isPending = row.original.statusNameEn === 'Pending';
        const copyDisabled = isPending || isCopying;
        const deleteDisabled = !isPending || isDeleting;
        const copyTitle = isPending
          ? (table.cannotCopyPending || 'Cannot copy pending requests')
          : (table.copyRequest || 'Copy Request');
        const deleteTitle = isPending
          ? (table.deleteRequest || 'Delete Request')
          : (table.canOnlyDeletePending || 'Can only delete pending requests');

        return (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 cursor-pointer"
              onClick={() => onView(row.original)}
              title={table.viewDetails || 'View Details'}
            >
              <Eye className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <span className="sr-only">{table.viewDetails || 'View Details'}</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 w-8 p-0 ${!copyDisabled ? 'cursor-pointer' : ''}`}
              onClick={() => onCopy(row.original)}
              disabled={copyDisabled}
              title={copyTitle}
            >
              <Copy className={`h-4 w-4 ${copyDisabled ? 'text-gray-400' : 'text-green-600 dark:text-green-400'}`} />
              <span className="sr-only">{table.copyRequest || 'Copy Request'}</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 w-8 p-0 ${!deleteDisabled ? 'cursor-pointer' : ''}`}
              onClick={() => onDelete(row.original)}
              disabled={deleteDisabled}
              title={deleteTitle}
            >
              <Trash2 className={`h-4 w-4 ${deleteDisabled ? 'text-gray-400' : 'text-red-600 dark:text-red-400'}`} />
              <span className="sr-only">{table.deleteRequest || 'Delete Request'}</span>
            </Button>
          </div>
        );
      },
    },
  ];
}
