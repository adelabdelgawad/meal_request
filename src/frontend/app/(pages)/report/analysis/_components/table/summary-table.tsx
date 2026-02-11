'use client';

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { EmployeeAnalytics } from '@/types/analytics.types';
import { useMemo } from 'react';
import { useLanguage, translate } from '@/hooks/use-language';

interface SummaryTableProps {
  data: EmployeeAnalytics[];
  loading?: boolean;
}

export function SummaryTable({ data, loading }: SummaryTableProps) {
  const { t } = useLanguage();
  const totalRequests = useMemo(() => {
    return data.reduce((sum, item) => sum + item.acceptedRequests, 0);
  }, [data]);

  // Sort data by accepted requests in descending order
  const sortedData = useMemo(() => {
    return [...data].sort((a, b) => b.acceptedRequests - a.acceptedRequests);
  }, [data]);

  if (loading) {
    return (
      <div className="border rounded-lg p-4">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded mb-4 w-48"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-4">
      <h3 className="text-lg font-bold text-gray-700 mb-4">
        {translate(t, 'analysis.stats.totalRequests')}: {totalRequests}
      </h3>
      <div className="overflow-x-auto">
        <Table id="requestsTable">
          <TableHeader>
            <TableRow>
              <TableHead>{translate(t, 'analysis.table.name')}</TableHead>
              <TableHead>{translate(t, 'analysis.table.totalApproved')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={2} className="text-center py-4 text-muted-foreground">
                  {translate(t, 'common.noData')}
                </TableCell>
              </TableRow>
            ) : (
              sortedData.map((item, index) => (
                <TableRow key={index}>
                  <TableCell className="py-2 px-4">{item.name}</TableCell>
                  <TableCell className="py-2 px-4">{item.acceptedRequests}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
