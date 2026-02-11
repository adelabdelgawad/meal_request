'use client';

import { useCallback, useMemo, useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import useSWR from 'swr';
import { useLanguage, translate } from '@/hooks/use-language';
import { DataTable } from '@/components/data-table';
import { Pagination } from '@/components/data-table';
import type { EmployeeAnalytics } from '@/types/analytics.types';
import { AnalysisStatusCards } from '../cards/analysis-status-cards';
import { DateRangePicker } from '../controls/date-range-picker';
import { LiveIndicator } from '@/app/(pages)/request/requests/_components/live-indicator';
import { EmployeeDetailsModal } from '../modal/employee-details-modal';
import { createColumns } from './columns';
import { clientApi } from '@/lib/http/axios-client';
import { Button } from '@/components/data-table';
import { ExportButton } from '@/components/data-table/actions/export-button';
import { BarChart3 } from 'lucide-react';
import { RequestsBarChart } from '../chart/requests-bar-chart';
import type { Table as TanStackTable } from '@tanstack/react-table';

interface AnalysisDataTableProps {
  initialData: EmployeeAnalytics[];
}

/**
 * Fetcher function for SWR - calls Next.js API route
 */
const fetcher = async (url: string): Promise<EmployeeAnalytics[]> => {
  const response = await clientApi.get<EmployeeAnalytics[]>(url);

  if (!response.ok) {
    throw new Error(response.error || 'Failed to fetch');
  }
  return response.data || [];
};

export function AnalysisDataTable({ initialData }: AnalysisDataTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useLanguage();

  // Read URL parameters - Initialize with today if not present
  // Use useMemo to prevent recalculation on every render
  const { defaultStartTime, defaultEndTime } = useMemo(() => {
    const today = new Date();
    const startTime = new Date(today.setHours(0, 0, 0, 0)).toISOString();
    const endTime = new Date(today.setHours(23, 59, 59, 999)).toISOString();
    return { defaultStartTime: startTime, defaultEndTime: endTime };
  }, []); // Empty deps - only calculate once on mount

  const startTime = searchParams?.get('startTime') || searchParams?.get('from_date') || defaultStartTime;
  const endTime = searchParams?.get('endTime') || searchParams?.get('to_date') || defaultEndTime;
  const currentPage = parseInt(searchParams?.get('page') || '1', 10);
  const pageSize = parseInt(searchParams?.get('limit') || '10', 10);

  // Modal states
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeAnalytics | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Online/Offline tracking
  const [isOnline, setIsOnline] = useState(true);
  const [lastSuccessfulFetch, setLastSuccessfulFetch] = useState<number>(() => Date.now());

  // Track initial load vs background refresh
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(false);

  // Build API URL with current filters
  const params = new URLSearchParams();
  if (startTime) params.append('start_time', startTime);
  if (endTime) params.append('end_time', endTime);

  const apiUrl = `/analytics?${params.toString()}`;

  // Get polling interval from environment variable (default: 60 seconds)
  const pollInterval = Number(process.env.NEXT_PUBLIC_ANALYSIS_POLL_INTERVAL) || 60000;

  // SWR hook for data fetching
  const { data: analyticsData = initialData, isValidating } = useSWR<EmployeeAnalytics[]>(
    apiUrl,
    fetcher,
    {
      fallbackData: initialData,
      revalidateOnMount: false,
      refreshInterval: pollInterval, // Configurable polling interval
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      revalidateIfStale: true,
      onSuccess: () => {
        setIsOnline(true);
        setLastSuccessfulFetch(Date.now());

        if (!hasLoadedOnce) {
          setHasLoadedOnce(true);
          setIsInitialLoading(false);
        }
      },
      onError: (err) => {
        console.error('[Analysis DataTable] SWR onError - Failed to fetch analytics:', err);
        setIsOnline(false);
        if (!hasLoadedOnce) {
          setIsInitialLoading(false);
        }
      },
    }
  );

  // Compute stats
  const stats = useMemo(() => {
    const totalRequests = analyticsData.reduce((sum, item) => sum + item.acceptedRequests, 0);
    return {
      totalEmployees: analyticsData.length,
      totalRequests,
    };
  }, [analyticsData]);

  // Sort data by accepted requests in descending order
  const sortedData = useMemo(() => {
    return [...analyticsData].sort((a, b) => b.acceptedRequests - a.acceptedRequests);
  }, [analyticsData]);

  // Paginate data client-side
  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return sortedData.slice(startIndex, endIndex);
  }, [sortedData, currentPage, pageSize]);

  // Only show loading state on initial load or filter changes
  const showLoadingState = isInitialLoading || (isValidating && !hasLoadedOnce);

  // Monitor connection status
  useEffect(() => {
    const checkInterval = setInterval(() => {
      const timeSinceLastFetch = Date.now() - lastSuccessfulFetch;
      if (timeSinceLastFetch > 65000) {
        setIsOnline(false);
      }
    }, 5000);

    return () => clearInterval(checkInterval);
  }, [lastSuccessfulFetch]);

  // Update URL when filters change - Run only once on mount
  useEffect(() => {
    // Initialize URL params if not present
    if (!searchParams?.get('startTime') && !searchParams?.get('from_date')) {
      const params = new URLSearchParams(searchParams?.toString());
      if (!params.get('startTime')) params.set('startTime', defaultStartTime);
      if (!params.get('endTime')) params.set('endTime', defaultEndTime);
      router.replace(`?${params.toString()}`, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run only once on mount

  // Filter handlers
  const handleStartTimeChange = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams?.toString());
      if (value) {
        params.set('startTime', value);
      } else {
        params.delete('startTime');
      }
      params.delete('page');
      router.push(`?${params.toString()}`, { scroll: false });
    },
    [searchParams, router]
  );

  const handleEndTimeChange = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams?.toString());
      if (value) {
        params.set('endTime', value);
      } else {
        params.delete('endTime');
      }
      params.delete('page');
      router.push(`?${params.toString()}`, { scroll: false });
    },
    [searchParams, router]
  );

  // Action handlers
  const handleView = useCallback((employee: EmployeeAnalytics) => {
    setSelectedEmployee(employee);
    setIsModalOpen(true);
  }, []);

  const handleModalClose = useCallback(() => {
    setIsModalOpen(false);
    setSelectedEmployee(null);
  }, []);

  // Export detailed handler
  const handleExportDetailed = useCallback(() => {
    const params = new URLSearchParams({
      startTime: startTime,
      endTime: endTime,
    });
    router.push(`/audit?${params.toString()}`);
  }, [startTime, endTime, router]);

  // Create columns with handlers
  const columns = useMemo(
    () => createColumns(t, handleView),
    [t, handleView]
  );

  // Header labels for export
  const exportHeaderLabels = useMemo(() => ({
    name: translate(t, 'analysis.table.employeeName') || 'Employee Name',
    acceptedRequests: translate(t, 'analysis.table.totalRequests') || 'Total Approved Requests',
  }), [t]);

  // Toolbar renderer for export buttons
  const renderToolbar = useCallback((table: TanStackTable<EmployeeAnalytics>) => {
    return (
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex gap-2">
          <ExportButton
            table={table}
            filename="analysis_data"
            page={currentPage}
            headerLabels={exportHeaderLabels}
          />
          <Button
            variant="default"
            size="default"
            onClick={handleExportDetailed}
            icon={<BarChart3 className="w-4 h-4" />}
            tooltip={translate(t, 'analysis.actions.exportDetailed') || 'Export Detailed'}
          >
            {translate(t, 'analysis.actions.exportDetailed') || 'Detailed'}
          </Button>
        </div>
      </div>
    );
  }, [currentPage, exportHeaderLabels, handleExportDetailed, t]);

  return (
    <div className="flex flex-col gap-4">
      {/* Status Cards */}
      <AnalysisStatusCards stats={stats} />

      {/* Filters */}
      <div className="bg-card rounded-lg border shadow-sm p-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 justify-between">
          <DateRangePicker
            startTime={startTime}
            endTime={endTime}
            onStartTimeChange={handleStartTimeChange}
            onEndTimeChange={handleEndTimeChange}
          />
          <LiveIndicator isLive={isOnline} isValidating={isValidating} />
        </div>
      </div>

      {/* Chart */}
      <RequestsBarChart data={analyticsData} loading={showLoadingState} />

      {/* Data Table */}
      <div className="flex flex-col bg-card border rounded-lg shadow-sm">
        <DataTable
          _data={paginatedData}
          columns={columns}
          _isLoading={showLoadingState}
          enableRowSelection={false}
          renderToolbar={renderToolbar}
        />

        {/* Pagination */}
        <Pagination
          totalItems={sortedData.length}
        />
      </div>

      {/* Employee Details Modal */}
      {selectedEmployee && (
        <EmployeeDetailsModal
          isOpen={isModalOpen}
          onClose={handleModalClose}
          employeeName={selectedEmployee.name}
          startTime={startTime}
          endTime={endTime}
        />
      )}
    </div>
  );
}
