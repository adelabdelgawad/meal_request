'use client';

import { ColumnDef } from '@tanstack/react-table';
import { MealRequest } from '@/types/meal-request.types';
import { StatusBadge } from './table/status-badge';
import { ActionButtons } from './table/action-buttons';
import { formatDateTime } from '@/lib/datetime-utils';

interface TableTranslations {
  id?: string;
  requester?: string;
  title?: string;
  requestTime?: string;
  closedTime?: string;
  notes?: string;
  mealType?: string;
  totalRequests?: string;
  accepted?: string;
  status?: string;
  actions?: string;
}

interface Translations {
  requests?: { table?: TableTranslations };
}

export function createColumns(
  t: Translations | null,
  locale: string,
  onView: (request: MealRequest) => void,
  onApprove: (requestId: number) => void,
  onReject: (requestId: number) => void,
  actionLoadingId?: number | null
): ColumnDef<MealRequest>[] {
  // Get translations from the requests.table namespace
  const table = t?.requests?.table || {};

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
      accessorKey: 'requesterName',
      header: table.requester || 'Requester',
      size: 150,
      cell: ({ row }) => (
        <div className="truncate">{row.original.requesterName}</div>
      ),
    },
    {
      accessorKey: 'requesterTitle',
      header: table.title || 'Title',
      size: 150,
      cell: ({ row }) => (
        <div className="truncate">{row.original.requesterTitle || '-'}</div>
      ),
    },
    {
      accessorKey: 'requestTime',
      header: table.requestTime || 'Request Time',
      size: 180,
      cell: ({ row }) => (
        <div className="text-sm">
          {formatDateTime(row.original.requestTime, 'dd/MM/yyyy HH:mm:ss', locale)}
        </div>
      ),
    },
    {
      accessorKey: 'closedTime',
      header: table.closedTime || 'Closed Time',
      size: 180,
      cell: ({ row }) => (
        <div className="text-sm">
          {row.original.closedTime
            ? formatDateTime(row.original.closedTime, 'dd/MM/yyyy HH:mm:ss', locale)
            : '-'}
        </div>
      ),
    },
    {
      accessorKey: 'notes',
      header: table.notes || 'Notes',
      size: 200,
      cell: ({ row }) => (
        <div className="truncate" title={row.original.notes || ''}>
          {row.original.notes || '-'}
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
        <div className="font-medium text-green-600">
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
      id: 'actions',
      header: table.actions || 'Actions',
      size: 150,
      cell: ({ row }) => (
        <ActionButtons
          requestId={row.original.mealRequestId}
          status={row.original.statusNameEn}
          onView={() => onView(row.original)}
          onApprove={async () => onApprove(row.original.mealRequestId)}
          onReject={async () => onReject(row.original.mealRequestId)}
          isActionLoading={actionLoadingId === row.original.mealRequestId}
        />
      ),
    },
  ];
}
