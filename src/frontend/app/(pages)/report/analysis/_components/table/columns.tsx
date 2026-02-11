'use client';

import { ColumnDef } from '@tanstack/react-table';
import type { EmployeeAnalytics } from '@/types/analytics.types';
import { Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';

/**
 * Create column definitions for the analysis data table
 */
export function createColumns(
  t: Record<string, unknown>,
  onView: (employee: EmployeeAnalytics) => void
): ColumnDef<EmployeeAnalytics>[] {
  // Safely access nested translation properties
  const analysisTranslations = (t?.analysis || {}) as Record<string, unknown>;
  const tableTranslations = (analysisTranslations?.table || {}) as Record<string, unknown>;
  const actionsTranslations = (analysisTranslations?.actions || {}) as Record<string, unknown>;

  return [
    {
      accessorKey: 'name',
      header: (tableTranslations?.employeeName as string) || 'Employee Name',
      cell: ({ row }) => (
        <div className="font-medium">{row.original.name}</div>
      ),
    },
    {
      accessorKey: 'acceptedRequests',
      header: (tableTranslations?.totalRequests as string) || 'Total Approved Requests',
      cell: ({ row }) => (
        <div className="font-semibold text-primary">
          {row.original.acceptedRequests}
        </div>
      ),
    },
    {
      id: 'actions',
      header: (tableTranslations?.actions as string) || 'Actions',
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onView(row.original)}
          className="h-8 gap-2"
        >
          <Eye className="h-4 w-4" />
          {(actionsTranslations?.viewDetails as string) || 'View Details'}
        </Button>
      ),
    },
  ];
}
