'use client';

import { useCallback, useMemo, useState, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import useSWR from 'swr';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { toast } from 'sonner';
import { updateMealRequestStatus } from '@/lib/api/meal-requests';
import type { MealRequest, MealRequestStats, PaginatedMealRequests, RequestLine, MealRequestStatusOption } from '@/types/meal-request.types';
import { getRequestLines } from '@/lib/actions/requests.actions';
import { StatusCards } from './status-cards';
import { CompactFilters } from './compact-filters';
import { TablePagination } from './table-pagination';
import { StatusBadge } from './table/status-badge';
import { ActionButtons } from './table/action-buttons';
import { RequestDetailsModal } from './modal/request-details-modal';
import { REQUEST_STATUS_IDS } from '@/types/meal-request.types';
import { format } from 'date-fns';
import { Loader2 } from 'lucide-react';
import { clientApi } from '@/lib/http/axios-client';
import { useSession } from '@/lib/auth/use-session';

interface RequestsTableProps {
  initialData: PaginatedMealRequests;
  initialStats: MealRequestStats;
  statusOptions: MealRequestStatusOption[];
}

// Default empty stats
const EMPTY_STATS: MealRequestStats = { total: 0, pending: 0, approved: 0, rejected: 0 };

// Default empty paginated response
const EMPTY_PAGINATED: PaginatedMealRequests = {
  items: [],
  total: 0,
  page: 1,
  page_size: 50,
  total_pages: 0,
  stats: EMPTY_STATS,
};

/**
 * Fetcher function for SWR - calls Next.js API route
 * Returns unified response with items + stats
 */
const fetcher = async (url: string): Promise<PaginatedMealRequests> => {
  const response = await clientApi.get<PaginatedMealRequests>(url);
  if (!response.ok) {
    throw new Error(response.error || 'Failed to fetch');
  }
  // Handle paginated response with stats
  if (response.data && typeof response.data === 'object' && 'items' in response.data) {
    // Ensure stats exists in response
    const data = response.data as PaginatedMealRequests;
    return {
      ...data,
      stats: data.stats || EMPTY_STATS,
    };
  }
  // Fallback for unexpected format
  return EMPTY_PAGINATED;
};

/**
 * Map status ID to status name for filter matching
 */
const STATUS_ID_TO_NAME: Record<number, string> = {
  [REQUEST_STATUS_IDS.PENDING]: 'Pending',
  [REQUEST_STATUS_IDS.APPROVED]: 'Approved',
  [REQUEST_STATUS_IDS.REJECTED]: 'Rejected',
};

/**
 * Get Arabic status name from English status name
 */
const getArabicStatusName = (englishName: string): string => {
  const arabicNames: Record<string, string> = {
    Pending: 'قيد الانتظار',
    Approved: 'مقبول',
    Rejected: 'مرفوض',
  };
  return arabicNames[englishName] || englishName;
};

export function RequestsTable({ initialData, initialStats, statusOptions }: RequestsTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useSession();

  // Read URL parameters
  const statusFilter = searchParams?.get('status') || '';
  const requesterFilter = searchParams?.get('requester') || '';
  const fromDate = searchParams?.get('from_date') || '';
  const toDate = searchParams?.get('to_date') || '';
  const currentPage = parseInt(searchParams?.get('page') || '1', 10);

  // Modal states
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);
  const [selectedRequestStatus, setSelectedRequestStatus] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [prefetchedLines, setPrefetchedLines] = useState<RequestLine[] | null>(null);
  const [isPrefetching, setIsPrefetching] = useState(false);
  const [prefetchingId, setPrefetchingId] = useState<number | null>(null);

  // Action loading state - track which request is being updated
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  // Ref to store previous data for rollback
  const previousDataRef = useRef<PaginatedMealRequests | null>(null);

  // Get authenticated user's ID
  const userId = user?.id || '';

  // Check if "to date" is in the future for live polling
  const isToDateInFuture = useMemo(() => {
    if (!toDate) return false;
    const toDateTime = new Date(toDate);
    const now = new Date();
    return toDateTime > now;
  }, [toDate]);

  // Build API URL with current filters
  const params = new URLSearchParams();
  if (statusFilter) params.append('status', statusFilter);
  if (requesterFilter) params.append('requester', requesterFilter);
  if (fromDate) params.append('from_date', fromDate);
  if (toDate) params.append('to_date', toDate);
  params.append('page', currentPage.toString());
  params.append('page_size', '50');

  // Note: clientApi already has baseURL="/api", so don't include /api/ prefix
  const apiUrl = `/meal-requests?${params.toString()}`;

  // Ensure initialData has stats (merge with initialStats for backward compatibility)
  const initialDataWithStats: PaginatedMealRequests = useMemo(() => ({
    ...initialData,
    stats: initialData.stats || initialStats || EMPTY_STATS,
  }), [initialData, initialStats]);

  // Single SWR hook for unified data (items + stats)
  const { data: paginatedData = initialDataWithStats, isValidating, mutate } = useSWR<PaginatedMealRequests>(
    apiUrl,
    fetcher,
    {
      // Use server-side data as initial cache
      fallbackData: initialDataWithStats,

      // Smooth transitions when changing filters
      keepPreviousData: true,

      // Don't refetch on mount (we have SSR data)
      revalidateOnMount: false,

      // Conditional polling for live updates (30 seconds if toDate is in future)
      refreshInterval: isToDateInFuture ? 30000 : 0,

      // Disable automatic refetch on focus, enable on reconnect
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      revalidateIfStale: true,
    }
  );

  // Derived values from unified cache
  const requests = paginatedData.items;
  const stats = paginatedData.stats || EMPTY_STATS;

  // Filter update handlers - update URL instead of local state
  const handleStatusChange = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams?.toString());
      if (value && value !== 'all') {
        params.set('status', value);
      } else {
        params.delete('status');
      }
      params.delete('page'); // Reset to page 1 when status changes
      router.push(`?${params.toString()}`, { scroll: false });
    },
    [searchParams, router]
  );

  const handleRequesterChange = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams?.toString());
      if (value) {
        params.set('requester', value);
      } else {
        params.delete('requester');
      }
      params.delete('page'); // Reset to page 1 when filter changes
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
      params.delete('page'); // Reset to page 1 when filter changes
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
      params.delete('page'); // Reset to page 1 when filter changes
      router.push(`?${params.toString()}`, { scroll: false });
    },
    [searchParams, router]
  );

  const handlePageChange = useCallback(
    (page: number) => {
      const params = new URLSearchParams(searchParams?.toString());
      params.set('page', page.toString());
      router.push(`?${params.toString()}`, { scroll: false });
    },
    [searchParams, router]
  );

  // Action handlers
  const handleView = useCallback(async (request: MealRequest) => {
    setPrefetchingId(request.mealRequestId);
    setIsPrefetching(true);

    try {
      // Prefetch request lines using server action
      const lines = await getRequestLines(request.mealRequestId);
      setPrefetchedLines(lines);

      // Set modal state after data is ready
      setSelectedRequestId(request.mealRequestId);
      setSelectedRequestStatus(request.statusNameEn);
      setIsModalOpen(true);
    } catch (error) {
      console.error('Failed to prefetch request lines:', error);
      toast.error('Failed to load request details. Please try again.');
    } finally {
      setIsPrefetching(false);
      setPrefetchingId(null);
    }
  }, []);

  /**
   * Optimistic update helper with filter-aware removal and rollback
   */
  const handleStatusUpdate = useCallback(
    async (requestId: number, newStatusId: number, actionName: string) => {
      if (!userId) {
        toast.error(`You must be logged in to ${actionName} requests`);
        return;
      }

      // Find the current request to get its previous status
      const currentRequest = requests.find((r) => r.mealRequestId === requestId);
      if (!currentRequest) {
        toast.error('Request not found');
        return;
      }

      const previousStatusId = currentRequest.statusId;
      const newStatusName = STATUS_ID_TO_NAME[newStatusId] || 'Unknown';

      // Check if the request will be removed from current filter after status change
      const willBeRemovedFromFilter =
        statusFilter &&
        statusFilter.toLowerCase() !== 'all' &&
        statusFilter.toLowerCase() !== newStatusName.toLowerCase();

      // Set loading state for this specific request
      setActionLoadingId(requestId);

      // Store current data for potential rollback
      previousDataRef.current = paginatedData;

      // Apply optimistic update immediately
      await mutate(
        (currentData) => {
          if (!currentData) return currentData;

          let updatedItems: MealRequest[];
          let newTotal = currentData.total;

          if (willBeRemovedFromFilter) {
            // Remove the item from the view (filter no longer matches)
            updatedItems = currentData.items.filter(
              (req) => req.mealRequestId !== requestId
            );
            newTotal = Math.max(0, currentData.total - 1);
          } else {
            // Update the item in place
            updatedItems = currentData.items.map((req) =>
              req.mealRequestId === requestId
                ? {
                    ...req,
                    statusId: newStatusId,
                    statusNameEn: newStatusName as MealRequest['statusNameEn'],
                    statusNameAr: getArabicStatusName(newStatusName) as MealRequest['statusNameAr'],
                    closedTime: new Date().toISOString(), // Optimistic closed time
                  }
                : req
            );
          }

          // Optimistically update stats
          const updatedStats = { ...currentData.stats };
          const prevStatusKey = STATUS_ID_TO_NAME[previousStatusId]?.toLowerCase() as keyof MealRequestStats;
          const newStatusKey = newStatusName.toLowerCase() as keyof MealRequestStats;

          if (prevStatusKey && typeof updatedStats[prevStatusKey] === 'number') {
            updatedStats[prevStatusKey] = Math.max(0, (updatedStats[prevStatusKey] as number) - 1);
          }
          if (newStatusKey && typeof updatedStats[newStatusKey] === 'number') {
            updatedStats[newStatusKey] = (updatedStats[newStatusKey] as number) + 1;
          }

          return {
            ...currentData,
            items: updatedItems,
            total: newTotal,
            total_pages: Math.ceil(newTotal / currentData.page_size),
            stats: updatedStats,
          };
        },
        { revalidate: false }
      );

      // Send request to server
      const result = await updateMealRequestStatus(requestId, newStatusId, userId);

      // Clear loading state
      setActionLoadingId(null);

      if (result.success && result.data) {
        toast.success(`Meal Request ID: ${requestId} has been ${actionName}d successfully`);

        // Update with server response data without triggering refetch
        await mutate(
          (currentData) => {
            if (!currentData) return currentData;

            if (willBeRemovedFromFilter) {
              // Item already removed optimistically, keep it that way
              return currentData;
            }

            // Update with server-returned data
            return {
              ...currentData,
              items: currentData.items.map((req) =>
                req.mealRequestId === requestId ? result.data! : req
              ),
            };
          },
          { revalidate: false } // No refetch - use optimistic update + server response
        );
      } else {
        // Rollback on error
        toast.error(result.error || `Failed to ${actionName} Meal Request ID: ${requestId}`);

        if (previousDataRef.current) {
          await mutate(previousDataRef.current, { revalidate: false });
        } else {
          // If no previous data, trigger full revalidation
          await mutate();
        }
      }

      previousDataRef.current = null;
    },
    [userId, requests, statusFilter, paginatedData, mutate]
  );

  const handleApprove = useCallback(
    (requestId: number) => handleStatusUpdate(requestId, REQUEST_STATUS_IDS.APPROVED, 'approve'),
    [handleStatusUpdate]
  );

  const handleReject = useCallback(
    (requestId: number) => handleStatusUpdate(requestId, REQUEST_STATUS_IDS.REJECTED, 'reject'),
    [handleStatusUpdate]
  );

  const handleModalClose = useCallback(() => {
    setIsModalOpen(false);
    setSelectedRequestId(null);
    setSelectedRequestStatus('');
    setPrefetchedLines(null);
    setPrefetchingId(null);
  }, []);

  const handleSaveSuccess = useCallback(() => {
    // Trigger background revalidation to sync with server
    mutate();
  }, [mutate]);

  return (
    <div className="flex flex-col gap-4 flex-1">
      {/* Status Cards */}
      <StatusCards
        stats={stats}
        currentStatus={statusFilter}
        statusOptions={statusOptions}
        onStatusClick={handleStatusChange}
      />

      {/* Compact Filters */}
      <CompactFilters
        fromDate={fromDate}
        toDate={toDate}
        requesterFilter={requesterFilter}
        isLive={isToDateInFuture}
        onFromDateChange={handleFromDateChange}
        onToDateChange={handleToDateChange}
        onRequesterChange={handleRequesterChange}
      />

      {/* Table */}
      <div className="bg-white border rounded-lg shadow-sm flex-1 overflow-hidden flex flex-col">
        <div className="overflow-auto flex-1">
          <Table>
            <TableHeader className="sticky top-0 bg-gray-100 z-10">
              <TableRow>
                <TableHead className="font-semibold">#</TableHead>
                <TableHead className="font-semibold">Requester</TableHead>
                <TableHead className="font-semibold">Title</TableHead>
                <TableHead className="font-semibold">Request Time</TableHead>
                <TableHead className="font-semibold">Closed Time</TableHead>
                <TableHead className="font-semibold">Notes</TableHead>
                <TableHead className="font-semibold">Type</TableHead>
                <TableHead className="font-semibold">Requests</TableHead>
                <TableHead className="font-semibold">Accepted</TableHead>
                <TableHead className="font-semibold">Status</TableHead>
                <TableHead className="font-semibold">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {requests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={11} className="text-center py-8">
                    {isValidating ? (
                      <div className="flex items-center justify-center gap-2">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        <span className="text-muted-foreground">Loading requests...</span>
                      </div>
                    ) : (
                      <div className="text-muted-foreground">
                        <p className="text-lg font-semibold mb-2">No Requests Found</p>
                        <p className="text-sm">Try adjusting your filters</p>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ) : (
                requests.map((request) => (
                  <TableRow key={request.mealRequestId} className="hover:bg-gray-50">
                    <TableCell>{request.mealRequestId}</TableCell>
                    <TableCell>{request.requesterName}</TableCell>
                    <TableCell>{request.requesterTitle || '-'}</TableCell>
                    <TableCell>
                      {format(new Date(request.requestTime), 'dd/MM/yyyy HH:mm:ss')}
                    </TableCell>
                    <TableCell>
                      {request.closedTime
                        ? format(new Date(request.closedTime), 'dd/MM/yyyy HH:mm:ss')
                        : '-'}
                    </TableCell>
                    <TableCell>{request.notes || '-'}</TableCell>
                    <TableCell>{request.mealTypeEn}</TableCell>
                    <TableCell>{request.totalRequestLines}</TableCell>
                    <TableCell>{request.acceptedRequestLines ?? 0}</TableCell>
                    <TableCell>
                      <StatusBadge status={request.statusNameEn} />
                    </TableCell>
                    <TableCell>
                      <ActionButtons
                        requestId={request.mealRequestId}
                        status={request.statusNameEn}
                        onView={() => handleView(request)}
                        onApprove={() => handleApprove(request.mealRequestId)}
                        onReject={() => handleReject(request.mealRequestId)}
                        isViewLoading={isPrefetching && prefetchingId === request.mealRequestId}
                        isActionLoading={actionLoadingId === request.mealRequestId}
                      />
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        <TablePagination
          currentPage={paginatedData.page}
          totalPages={paginatedData.total_pages}
          total={paginatedData.total}
          pageSize={paginatedData.page_size}
          onPageChange={handlePageChange}
        />
      </div>

      {/* Details Modal */}
      {selectedRequestId && userId && (
        <RequestDetailsModal
          isOpen={isModalOpen}
          onClose={handleModalClose}
          requestId={selectedRequestId}
          requestStatus={selectedRequestStatus}
          userId={userId}
          onSaveSuccess={handleSaveSuccess}
          initialLines={prefetchedLines || undefined}
        />
      )}
    </div>
  );
}
