'use client';

import { useCallback, useMemo, useState, useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import useSWR from 'swr';
import { useLanguage } from '@/hooks/use-language';
import { DataTable } from '@/components/data-table';
import { Pagination } from '@/components/data-table';
import type { MealRequest, MealRequestStats, PaginatedMealRequests, MealRequestStatusOption } from '@/types/meal-request.types';
import { StatusCards } from '../../requests/_components/status-cards';
import { HistoryTableController } from './table/history-table-controller';
import { HistoryDetailsModal } from './history-details-modal';
import { clientApi } from '@/lib/http/axios-client';
import { createHistoryColumns } from './history-columns';
import { History } from 'lucide-react';
import { toast } from 'sonner';
import { copyMealRequest } from '@/lib/actions/requests.actions';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';

interface HistoryDataTableProps {
  initialData: PaginatedMealRequests;
  initialStats: MealRequestStats;
  statusOptions: MealRequestStatusOption[];
}

// Default empty stats for fallback
const EMPTY_STATS: MealRequestStats = { total: 0, pending: 0, approved: 0, rejected: 0 };

/**
 * Fetcher function for SWR - calls Next.js API route for user's own requests
 */
const fetcher = async (url: string): Promise<PaginatedMealRequests> => {
  const response = await clientApi.get<PaginatedMealRequests>(url);
  if (!response.ok) {
    throw new Error(response.error || 'Failed to fetch');
  }
  // Handle paginated response with stats
  if (response.data && typeof response.data === 'object' && 'items' in response.data) {
    const data = response.data as PaginatedMealRequests;
    return {
      ...data,
      stats: data.stats || EMPTY_STATS,
    };
  }
  // Fallback for unexpected format
  return { items: [], total: 0, page: 1, page_size: 10, total_pages: 0, stats: EMPTY_STATS };
};

export function HistoryDataTable({ initialData, initialStats, statusOptions }: HistoryDataTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t, language: locale } = useLanguage();

  // Read URL parameters
  const statusFilter = searchParams?.get('status') || '';
  const fromDate = searchParams?.get('from_date') || '';
  const toDate = searchParams?.get('to_date') || '';
  const currentPage = parseInt(searchParams?.get('page') || '1', 10);
  const pageSize = parseInt(searchParams?.get('limit') || '10', 10);

  // Modal states
  const [selectedRequest, setSelectedRequest] = useState<MealRequest | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Copy state
  const [isCopying, setIsCopying] = useState(false);

  // Delete state
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [requestToDelete, setRequestToDelete] = useState<MealRequest | null>(null);

  // Online/Offline tracking
  const [isOnline, setIsOnline] = useState(true);
  const [lastSuccessfulFetch, setLastSuccessfulFetch] = useState<number>(Date.now());

  // Track initial load vs background refresh
  const isInitialLoadRef = useRef(true);
  const [isInitialLoading, setIsInitialLoading] = useState(false);

  // Track recently updated items for visual feedback
  const [highlightedIds, setHighlightedIds] = useState<Set<number>>(new Set());
  const previousDataRef = useRef<PaginatedMealRequests | undefined>(undefined);

  // Build API URL with current filters (uses /my-requests endpoint)
  const params = new URLSearchParams();
  if (statusFilter && statusFilter !== 'all') {
    params.append('status_id', statusFilter);
  }
  if (fromDate) params.append('from_date', fromDate);
  if (toDate) params.append('to_date', toDate);
  params.append('page', currentPage.toString());
  params.append('page_size', pageSize.toString());

  const apiUrl = `/my-requests?${params.toString()}`;

  // Ensure initialData has stats
  const initialDataWithStats: PaginatedMealRequests = useMemo(() => ({
    ...initialData,
    stats: initialData.stats || initialStats || EMPTY_STATS,
  }), [initialData, initialStats]);

  // SWR hook for unified data
  // Get polling interval from environment variable (default: 60 seconds)
  const pollInterval = Number(process.env.NEXT_PUBLIC_HISTORY_POLL_INTERVAL) || 60000;

  const { data: paginatedData = initialDataWithStats, isValidating, mutate } = useSWR<PaginatedMealRequests>(
    apiUrl,
    fetcher,
    {
      fallbackData: initialDataWithStats,
      keepPreviousData: true,
      revalidateOnMount: false,
      refreshInterval: pollInterval, // Configurable polling interval
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      revalidateIfStale: true,
      onSuccess: (newData) => {
        setIsOnline(true);
        setLastSuccessfulFetch(Date.now());

        if (isInitialLoadRef.current) {
          isInitialLoadRef.current = false;
          setIsInitialLoading(false);
        }

        // Track updated items for highlight effect
        if (previousDataRef.current && newData) {
          const existingMap = new Map(
            previousDataRef.current.items.map(item => [item.mealRequestId, item])
          );

          const changedIds = new Set<number>();
          for (const newItem of newData.items) {
            const existing = existingMap.get(newItem.mealRequestId);
            if (!existing || JSON.stringify(existing) !== JSON.stringify(newItem)) {
              changedIds.add(newItem.mealRequestId);
            }
          }

          if (changedIds.size > 0) {
            setHighlightedIds(changedIds);
            setTimeout(() => setHighlightedIds(new Set()), 2000);
          }
        }

        previousDataRef.current = newData;
      },
      onError: (err) => {
        console.error('Failed to fetch history requests:', err);
        setIsOnline(false);
        if (isInitialLoadRef.current) {
          setIsInitialLoading(false);
        }
      },
    }
  );

  // Initialize previous data ref on mount
  useEffect(() => {
    if (!previousDataRef.current && paginatedData.items.length > 0) {
      previousDataRef.current = paginatedData;
    }
  }, [paginatedData]);

  // Derived values
  const requests = paginatedData.items;
  const stats = paginatedData.stats || EMPTY_STATS;

  // Only show loading state on initial load
  const showLoadingState = isInitialLoading || (isValidating && isInitialLoadRef.current);

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

  // Filter handlers
  const handleStatusChange = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams?.toString());
      if (value && value !== 'all') {
        params.set('status', value);
      } else {
        params.delete('status');
      }
      params.delete('page');
      router.push(`?${params.toString()}`, { scroll: false });
    },
    [searchParams, router]
  );

  const handleFromDateChange = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams?.toString());
      if (value) {
        params.set('from_date', value);
      } else {
        params.delete('from_date');
      }
      params.delete('page');
      router.push(`?${params.toString()}`, { scroll: false });
    },
    [searchParams, router]
  );

  const handleToDateChange = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams?.toString());
      if (value) {
        params.set('to_date', value);
      } else {
        params.delete('to_date');
      }
      params.delete('page');
      router.push(`?${params.toString()}`, { scroll: false });
    },
    [searchParams, router]
  );

  // Get translations (needed before handlers that use it)
  const myRequestsT = useMemo(() => (t?.myRequests || {}) as Record<string, unknown>, [t]);
  const isRtl = locale === 'ar';

  // View handler
  const handleView = useCallback((request: MealRequest) => {
    setSelectedRequest(request);
    setIsModalOpen(true);
  }, []);

  const handleModalClose = useCallback(() => {
    setIsModalOpen(false);
    setSelectedRequest(null);
  }, []);

  // Copy handler
  const handleCopy = useCallback(async (request: MealRequest) => {
    if (isCopying) return;

    setIsCopying(true);
    try {
      const result = await copyMealRequest(request.mealRequestId);

      if (result.success && result.data) {
        toast.success(
          (myRequestsT.copySuccess as string) || 'Request copied successfully',
          {
            description: myRequestsT.copySuccessMessage
              ? (myRequestsT.copySuccessMessage as string).replace('{id}', result.data.newMealRequestId.toString())
              : `New request #${result.data.newMealRequestId} created with ${result.data.linesCopied} lines`,
          }
        );

        // Refresh the list to show the new request
        mutate();
      } else {
        toast.error(
          (myRequestsT.copyError as string) || 'Copy failed',
          {
            description: result.error || 'Failed to copy request',
          }
        );
      }
    } catch (error) {
      console.error('Copy request error:', error);
      toast.error(
        (myRequestsT.copyError as string) || 'Copy failed',
        {
          description: 'An unexpected error occurred',
        }
      );
    } finally {
      setIsCopying(false);
    }
  }, [isCopying, mutate, myRequestsT]);

  // Delete handler - show confirmation dialog
  const handleDelete = useCallback((request: MealRequest) => {
    // Only allow deletion of PENDING requests
    if (request.statusNameEn !== 'Pending') {
      toast.error(
        (myRequestsT.deleteError as string) || 'Cannot delete request',
        {
          description: ((myRequestsT.table as Record<string, unknown>)?.canOnlyDeletePending as string) || 'Only PENDING requests can be deleted',
        }
      );
      return;
    }

    setRequestToDelete(request);
    setDeleteConfirmOpen(true);
  }, [myRequestsT]);

  // Confirm delete handler
  const handleConfirmDelete = useCallback(async () => {
    if (!requestToDelete || isDeleting) return;

    setIsDeleting(true);
    try {
      const response = await clientApi.delete(
        `/v1/requests/${requestToDelete.mealRequestId}/soft-delete`
      );

      if (response.ok) {
        // Interpolate values in success message
        const successMessage = ((myRequestsT.deleteSuccessMessage as string) ||
          'Request #{{requestId}} and its {{totalLines}} lines have been deleted')
          .replace('{{requestId}}', requestToDelete.mealRequestId.toString())
          .replace('{{totalLines}}', requestToDelete.totalRequestLines.toString());

        toast.success(
          (myRequestsT.deleteSuccess as string) || 'Request deleted successfully',
          {
            description: successMessage,
          }
        );

        // Refresh the list to remove the deleted request
        mutate();
      } else {
        toast.error(
          (myRequestsT.deleteError as string) || 'Delete failed',
          {
            description: response.error || 'Failed to delete request',
          }
        );
      }
    } catch (error) {
      console.error('Delete request error:', error);
      toast.error(
        (myRequestsT.deleteError as string) || 'Delete failed',
        {
          description: 'An unexpected error occurred while deleting the request',
        }
      );
    } finally {
      setIsDeleting(false);
      setRequestToDelete(null);
    }
  }, [requestToDelete, isDeleting, mutate, myRequestsT]);

  // Create columns (view, copy, and delete actions)
  const columns = useMemo(
    () => createHistoryColumns(t, locale, handleView, handleCopy, handleDelete, isCopying, isDeleting),
    [t, locale, handleView, handleCopy, handleDelete, isCopying, isDeleting]
  );

  // Row highlight for updates
  const getRowClassName = useCallback(
    (row: MealRequest) => {
      if (highlightedIds.has(row.mealRequestId)) {
        return 'animate-highlight-row';
      }
      return '';
    },
    [highlightedIds]
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Page Header */}
      <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse justify-end' : ''}`}>
        <div className="p-2 rounded-lg bg-primary/10">
          <History className="h-6 w-6 text-primary" />
        </div>
        <div className={isRtl ? 'text-right' : ''}>
          <h1 className="text-2xl font-bold text-foreground">
            {(myRequestsT.title as string) || 'My Requests'}
          </h1>
          <p className="text-sm text-muted-foreground">
            {(myRequestsT.description as string) || 'View and track all your submitted meal requests'}
          </p>
        </div>
      </div>

      {/* Status Cards */}
      <StatusCards
        stats={stats}
        currentStatus={statusFilter}
        statusOptions={statusOptions}
        onStatusClick={handleStatusChange}
      />

      {/* Table Controller */}
      <HistoryTableController
        fromDate={fromDate}
        toDate={toDate}
        isLive={isOnline}
        isValidating={isValidating}
        onFromDateChange={handleFromDateChange}
        onToDateChange={handleToDateChange}
      />

      {/* Data Table */}
      <div className="flex flex-col bg-card border rounded-lg shadow-sm">
        <DataTable
          _data={requests}
          columns={columns}
          _isLoading={showLoadingState}
          enableRowSelection={false}
          getRowClassName={getRowClassName}
        />

        {/* Pagination */}
        <Pagination
          totalItems={paginatedData.total}
        />
      </div>

      {/* Read-only Details Modal */}
      {selectedRequest && (
        <HistoryDetailsModal
          isOpen={isModalOpen}
          onClose={handleModalClose}
          request={selectedRequest}
        />
      )}

      {/* Delete Confirmation Dialog */}
      {requestToDelete && (
        <ConfirmDialog
          isOpen={deleteConfirmOpen}
          onClose={() => {
            setDeleteConfirmOpen(false);
            setRequestToDelete(null);
          }}
          onConfirm={handleConfirmDelete}
          title={((myRequestsT.deleteRequest as Record<string, unknown>)?.title as string) || 'Delete Request?'}
          message={
            ((myRequestsT.deleteRequest as Record<string, unknown>)?.message as string ||
              'Are you sure you want to delete request #{{requestId}}? This will remove all {{totalLines}} request lines. This action cannot be undone.')
              .replace('{{requestId}}', requestToDelete.mealRequestId.toString())
              .replace('{{totalLines}}', requestToDelete.totalRequestLines.toString())
          }
          confirmText={((myRequestsT.deleteRequest as Record<string, unknown>)?.confirm as string) || 'Delete'}
          cancelText={((myRequestsT.deleteRequest as Record<string, unknown>)?.cancel as string) || 'Cancel'}
          isRtl={isRtl}
          variant="destructive"
          isLoading={isDeleting}
        />
      )}
    </div>
  );
}
