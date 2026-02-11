"use client";

import React from 'react';
import { MealRequest } from '@/types/meal-request.types';
import { DataCard, DataCardField, DataCardAction } from '@/components/data-table/mobile/data-card';
import { StatusBadge } from '../table/status-badge';
import { formatDateTime } from '@/lib/datetime-utils';
import { Eye, CheckCircle, XCircle } from 'lucide-react';

interface RequestCardProps {
  request: MealRequest;
  locale: string;
  translations: {
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
    view?: string;
    approve?: string;
    reject?: string;
  };
  onView: (request: MealRequest) => void;
  onApprove: (requestId: number) => void;
  onReject: (requestId: number) => void;
  isActionLoading?: boolean;
}

/**
 * Mobile-optimized card for displaying meal request data.
 */
export function RequestCard({
  request,
  locale,
  translations,
  onView,
  onApprove,
  onReject,
  isActionLoading = false,
}: RequestCardProps) {
  const localizedMealType = locale === 'ar' ? request.mealTypeAr : request.mealTypeEn;
  const localizedStatus = locale === 'ar' ? request.statusNameAr : request.statusNameEn;

  // Build fields array
  const fields: DataCardField[] = [
    {
      label: translations.requester || 'Requester',
      value: request.requesterName,
    },
    {
      label: translations.title || 'Title',
      value: request.requesterTitle || '-',
    },
    {
      label: translations.mealType || 'Meal Type',
      value: localizedMealType,
    },
    {
      label: translations.requestTime || 'Request Time',
      value: formatDateTime(request.requestTime, 'dd/MM/yyyy HH:mm', locale),
    },
    {
      label: translations.totalRequests || 'Total',
      value: (
        <span className="font-medium">{request.totalRequestLines}</span>
      ),
    },
    {
      label: translations.accepted || 'Accepted',
      value: (
        <span className="font-medium text-green-600">
          {request.acceptedRequestLines ?? 0}
        </span>
      ),
    },
  ];

  // Add optional fields
  if (request.closedTime) {
    fields.push({
      label: translations.closedTime || 'Closed Time',
      value: formatDateTime(request.closedTime, 'dd/MM/yyyy HH:mm', locale),
      fullWidth: true,
    });
  }

  if (request.notes) {
    fields.push({
      label: translations.notes || 'Notes',
      value: request.notes,
      fullWidth: true,
      className: 'text-muted-foreground',
    });
  }

  // Build actions based on status
  const actions: DataCardAction[] = [
    {
      label: translations.view || 'View',
      onClick: () => onView(request),
      variant: 'outline',
      icon: <Eye className="h-4 w-4" />,
    },
  ];

  // Add approve/reject buttons for pending requests
  if (request.statusNameEn === 'Pending') {
    actions.push(
      {
        label: translations.approve || 'Approve',
        onClick: () => onApprove(request.mealRequestId),
        variant: 'default',
        icon: <CheckCircle className="h-4 w-4" />,
        disabled: isActionLoading,
      },
      {
        label: translations.reject || 'Reject',
        onClick: () => onReject(request.mealRequestId),
        variant: 'destructive',
        icon: <XCircle className="h-4 w-4" />,
        disabled: isActionLoading,
      }
    );
  }

  return (
    <DataCard
      title={`#${request.mealRequestId}`}
      badge={<StatusBadge status={request.statusNameEn} label={localizedStatus} />}
      fields={fields}
      actions={actions}
      className={isActionLoading ? 'opacity-50 pointer-events-none' : ''}
    />
  );
}
