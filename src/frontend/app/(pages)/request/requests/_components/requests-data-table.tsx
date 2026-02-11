'use client';

import { useCallback, useMemo, useState, useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import useSWR from 'swr';
import { toast } from 'sonner';
import { useLanguage } from '@/hooks/use-language';
import { DataTable } from '@/components/data-table';
import { Pagination } from '@/components/data-table';
import type { MealRequest, MealRequestStats, PaginatedMealRequests, MealRequestStatusOption } from '@/types/meal-request.types';
import { StatusCards } from './status-cards';
import { RequestsTableController } from './table/requests-table-controller';
import { RequestDetailsModal } from './modal/request-details-modal';
import { REQUEST_STATUS_IDS } from '@/types/meal-request.types';
import { updateMealRequestStatus } from '@/lib/api/meal-requests';
import { clientApi } from '@/lib/http/axios-client';
import { useSession } from '@/lib/auth/use-session';
import { createColumns } from './columns';
import { RequestCard } from './mobile/request-card';

/**
 * Merge new paginated data with existing data smoothly
 * - Updates existing items in place
 * - Adds new items to the beginning
 * - Returns IDs of new/updated items for visual feedback
 */
function mergeRequestsData(
  existingData: PaginatedMealRequests | undefined,
  newData: PaginatedMealRequests
): { merged: PaginatedMealRequests; updatedIds: Set<number>; newIds: Set<number> } {
  if (!existingData) {
    return {
      merged: newData,
      updatedIds: new Set(),
      newIds: new Set(newData.items.map(item => item.mealRequestId))
    };
  }

  const existingMap = new Map(
    existingData.items.map(item => [item.mealRequestId, item])
  );

  const updatedIds = new Set<number>();
  const newIds = new Set<number>();

  // Check each new item
  for (const newItem of newData.items) {
    const existing = existingMap.get(newItem.mealRequestId);
    if (!existing) {
      newIds.add(newItem.mealRequestId);
    } else if (JSON.stringify(existing) !== JSON.stringify(newItem)) {
      updatedIds.add(newItem.mealRequestId);
    }
  }

  return {
    merged: newData,
    updatedIds,
    newIds,
  };
}

interface RequestsDataTableProps {
  initialData: PaginatedMealRequests;
  initialStats: MealRequestStats;
  statusOptions: MealRequestStatusOption[];
}

// Default empty stats for fallback
const EMPTY_STATS: MealRequestStats = { total: 0, pending: 0, approved: 0, rejected: 0 };

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
    const data = response.data as PaginatedMealRequests;
    return {
      ...data,
      stats: data.stats || EMPTY_STATS,
    };
  }
  // Fallback for unexpected format
  return { items: [], total: 0, page: 1, page_size: 10, total_pages: 0, stats: EMPTY_STATS };
};

export function RequestsDataTable({ initialData, initialStats, statusOptions }: RequestsDataTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useSession();
  const { t, language: locale } = useLanguage();

  // Read URL parameters
  const statusFilter = searchParams?.get('status') || ''; // Status ID as string
  const requesterFilter = searchParams?.get('requester') || '';
  const fromDate = searchParams?.get('from_date') || '';
  const toDate = searchParams?.get('to_date') || '';
  const currentPage = parseInt(searchParams?.get('page') || '1', 10);
  const pageSize = parseInt(searchParams?.get('limit') || '10', 10);

  // Modal states
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);
  const [selectedRequestStatus, setSelectedRequestStatus] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Action loading state - track which request is being updated
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  // Online/Offline tracking
  const [isOnline, setIsOnline] = useState(true);
  const [lastSuccessfulFetch, setLastSuccessfulFetch] = useState<number>(() => Date.now());

  // Track initial load vs background refresh
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(false);

  // Track recently updated/new items for visual feedback
  const [highlightedIds, setHighlightedIds] = useState<Set<number>>(new Set());
  const previousDataRef = useRef<PaginatedMealRequests | undefined>(undefined);

  // Get authenticated user's ID
  const userId = user?.id || '';

  // Build API URLs for stats and items
  const statsParams = new URLSearchParams();
  if (requesterFilter) statsParams.append('requester', requesterFilter);
  if (fromDate) statsParams.append('from_date', fromDate);
  if (toDate) statsParams.append('to_date', toDate);
  // Stats endpoint - no status filter, no pagination
  const statsUrl = `/meal-requests/stats?${statsParams.toString()}`;

  const itemsParams = new URLSearchParams();
  if (statusFilter && statusFilter !== 'all') {
    itemsParams.append('status_id', statusFilter);
  }
  if (requesterFilter) itemsParams.append('requester', requesterFilter);
  if (fromDate) itemsParams.append('from_date', fromDate);
  if (toDate) itemsParams.append('to_date', toDate);
  itemsParams.append('page', currentPage.toString());
  itemsParams.append('page_size', pageSize.toString());
  const itemsUrl = `/meal-requests?${itemsParams.toString()}`;

  // Ensure initialData has stats (merge with initialStats for backward compatibility)
  const initialDataWithStats: PaginatedMealRequests = useMemo(() => ({
    ...initialData,
    stats: initialData.stats || initialStats || EMPTY_STATS,
  }), [initialData, initialStats]);

  // Check if any filters are active (input or date-time filters)
  const hasActiveFilters = Boolean(requesterFilter || fromDate || toDate);

  // Get polling interval from environment variable (default: 30 seconds)
  // Disable polling when filters are active
  const basePollInterval = Number(process.env.NEXT_PUBLIC_REQUESTS_POLL_INTERVAL) || 30000;
  const pollInterval = hasActiveFilters ? 0 : basePollInterval;

  // SWR hook for stats - polls at configured interval unless filters are active
  const { data: statsData = initialStats || EMPTY_STATS, mutate: mutateStats } = useSWR<MealRequestStats>(
    statsUrl,
    async (url: string) => {
      const response = await clientApi.get<MealRequestStats>(url);
      if (!response.ok) {
        throw new Error(response.error || 'Failed to fetch stats');
      }
      return response.data || EMPTY_STATS;
    },
    {
      fallbackData: initialStats || EMPTY_STATS,
      revalidateOnMount: false,
      refreshInterval: pollInterval, // Disabled when filters are active
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      revalidateIfStale: true,
      onSuccess: () => {
        setIsOnline(true);
        setLastSuccessfulFetch(Date.now());
      },
      onError: (err) => {
        console.error('Failed to fetch stats:', err);
        setIsOnline(false);
      },
    }
  );

  // SWR hook for items - polls when on page 1 AND no filters are active
  const { data: paginatedData = initialDataWithStats, isValidating, mutate } = useSWR<PaginatedMealRequests>(
    itemsUrl,
    fetcher,
    {
      fallbackData: initialDataWithStats,
      revalidateOnMount: false,
      // Conditional polling: only poll when on page 1 AND no filters are active
      refreshInterval: currentPage === 1 ? pollInterval : 0,
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      revalidateIfStale: true,
      onSuccess: (newData) => {
        setIsOnline(true);
        setLastSuccessfulFetch(Date.now());

        // After initial load, mark as loaded
        if (!hasLoadedOnce) {
          setHasLoadedOnce(true);
          setIsInitialLoading(false);
        }

        // Track new/updated items for subtle highlight effect (only on page 1)
        if (currentPage === 1 && previousDataRef.current && newData) {
          const { updatedIds, newIds } = mergeRequestsData(previousDataRef.current, newData);

          // Combine new and updated IDs
          const allChangedIds = new Set([...updatedIds, ...newIds]);

          if (allChangedIds.size > 0) {
            setHighlightedIds(allChangedIds);
            // Clear highlights after animation
            setTimeout(() => setHighlightedIds(new Set()), 2000);
          }
        }

        // Store current data for next comparison
        previousDataRef.current = newData;
      },
      onError: (err) => {
        console.error('Failed to fetch meal requests:', err);
        setIsOnline(false);
        if (!hasLoadedOnce) {
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

  // Derived values - items from paginatedData, stats from separate statsData
  const requests = paginatedData.items;
  const stats = statsData;

  // Only show loading state on initial load or filter changes, not background refreshes
  const showLoadingState = isInitialLoading || (isValidating && !hasLoadedOnce);

  // Monitor connection status - mark offline if no successful fetch in 35 seconds
  useEffect(() => {
    const checkInterval = setInterval(() => {
      const timeSinceLastFetch = Date.now() - lastSuccessfulFetch;
      if (timeSinceLastFetch > 35000) {
        setIsOnline(false);
      }
    }, 5000); // Check every 5 seconds

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

  const handleRequesterChange = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams?.toString());
      if (value) {
        params.set('requester', value);
      } else {
        params.delete('requester');
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

  // Action handlers
  const handleView = useCallback((request: MealRequest) => {
    setSelectedRequestId(request.mealRequestId);
    setSelectedRequestStatus(request.statusNameEn); // Always use English for status logic
    setIsModalOpen(true);
  }, [setSelectedRequestId, setSelectedRequestStatus, setIsModalOpen]);

  /**
   * Helper to update requests in SWR cache (following users/roles pattern)
   * Pass updated request directly, builds new data object
   */
  const updateRequest = useCallback(
    async (updatedRequest: MealRequest, previousStatusId?: number) => {
      // Use current data from component scope (works with fallbackData)
      const currentData = paginatedData;

      if (!currentData) {
        return;
      }

      // Update request in the items list
      const updatedItems = currentData.items.map((req) =>
        req.mealRequestId === updatedRequest.mealRequestId ? updatedRequest : req
      );

      // Build new data object (without stats since they come from separate hook)
      const newData: PaginatedMealRequests = {
        ...currentData,
        items: updatedItems,
      };

      // Pass new data directly to mutate (NOT as an updater function - this is key!)
      await mutate(newData, { revalidate: false });

      // If status changed, trigger stats revalidation
      if (previousStatusId !== undefined && previousStatusId !== updatedRequest.statusId) {
        await mutateStats();
      }

      // Update previousDataRef to prevent false highlight detection on next update
      previousDataRef.current = newData;
    },
    [paginatedData, mutate, mutateStats]
  );

  /**
   * Helper to remove a request from the cache
   */
  const removeRequest = useCallback(
    async (requestId: number) => {
      const currentData = paginatedData;

      if (!currentData) {
        return;
      }

      const filteredItems = currentData.items.filter(
        (req) => req.mealRequestId !== requestId
      );
      const newTotal = Math.max(0, currentData.total - 1);

      const newData: PaginatedMealRequests = {
        ...currentData,
        items: filteredItems,
        total: newTotal,
        total_pages: Math.ceil(newTotal / currentData.page_size),
      };

      // Pass new data directly to mutate
      await mutate(newData, { revalidate: false });

      // Trigger stats revalidation since a request was removed/status changed
      await mutateStats();

      // Update previousDataRef to prevent false highlight detection on next update
      previousDataRef.current = newData;
    },
    [paginatedData, mutate, mutateStats]
  );

  /**
   * Unified status update handler - follows users/roles pattern
   */
  const handleStatusUpdate = useCallback(
    async (requestId: number, newStatusId: number, actionName: 'approve' | 'reject') => {
      if (!userId) {
        toast.error(((t?.requests as Record<string, unknown>)?.error as string) || 'You must be logged in');
        return;
      }

      // Find the current request to get its previous status
      const currentRequest = requests.find((r) => r.mealRequestId === requestId);
      if (!currentRequest) {
        toast.error('Request not found');
        return;
      }

      const previousStatusId = currentRequest.statusId;

      // Check if the request will be removed from current filter after status change
      const willBeRemovedFromFilter =
        statusFilter &&
        statusFilter !== 'all' &&
        statusFilter !== String(newStatusId);

      // Store current data for potential rollback
      const rollbackData = paginatedData;

      // Set loading state for this specific request
      setActionLoadingId(requestId);

      // Send request to server with expected status for concurrency control
      const result = await updateMealRequestStatus(requestId, newStatusId, userId, previousStatusId);

      // Clear loading state
      setActionLoadingId(null);

      if (result.success && result.data) {
        const requestTranslations = (t?.requests as Record<string, unknown>) || {};
        const successTranslations = (requestTranslations.success as Record<string, unknown>) || {};
        const successMsg = actionName === 'approve'
          ? ((successTranslations.approved as string) || 'Request approved successfully')
          : ((successTranslations.rejected as string) || 'Request rejected successfully');
        toast.success(successMsg);


        // Update cache with server response using the simple pattern
        if (willBeRemovedFromFilter) {
          await removeRequest(requestId);
        } else {
          await updateRequest(result.data, previousStatusId);
        }
      } else {
        // Rollback on error
        if (rollbackData) {
          await mutate(rollbackData, { revalidate: false });
        }

        // Handle concurrency conflict specifically
        if (result.isConflict) {
          const requestTranslations = (t?.requests as Record<string, unknown>) || {};
          const errorTranslations = (requestTranslations.error as Record<string, unknown>) || {};
          const conflictMsg = (errorTranslations.conflict as string) ||
            'This request has already been updated by another user. Refreshing data...';
          toast.warning(conflictMsg, {
            duration: 5000,
            description: (errorTranslations.conflictDescription as string) ||
              'The page will refresh to show the latest status.',
          });

          // Trigger full revalidation to get the latest data
          await mutate();
        } else {
          const requestTranslations = (t?.requests as Record<string, unknown>) || {};
          const errorTranslations = (requestTranslations.error as Record<string, unknown>) || {};
          const errorMsg = actionName === 'approve'
            ? ((errorTranslations.approve as string) || 'Failed to approve request')
            : ((errorTranslations.reject as string) || 'Failed to reject request');
          toast.error(result.error || errorMsg);

          if (!rollbackData) {
            await mutate();
          }
        }
      }
    },
    [userId, requests, statusFilter, paginatedData, mutate, t, removeRequest, updateRequest]
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
  }, [setIsModalOpen, setSelectedRequestId, setSelectedRequestStatus]);

  const handleSaveSuccess = useCallback(() => {
    // Trigger background revalidation to sync with server (includes stats in unified response)
    mutate();
  }, [mutate]);

  // Create columns with handlers
  const columns = useMemo(
    // eslint-disable-next-line react-hooks/refs
    () => createColumns(t, locale, handleView, handleApprove, handleReject, actionLoadingId),
    [t, locale, handleView, handleApprove, handleReject, actionLoadingId]
  );

  // Add highlight class to rows that were recently updated/added
  const getRowClassName = useCallback(
    (row: MealRequest) => {
      if (highlightedIds.has(row.mealRequestId)) {
        return 'animate-highlight-row';
      }
      return '';
    },
    [highlightedIds]
  );

  // Mobile card renderer
  const renderMobileCard = useCallback(
    (request: MealRequest) => {
      const tableTranslations = ((t?.requests as Record<string, unknown>)?.table || {}) as Record<string, unknown>;
      const commonTranslations = (t?.common || {}) as Record<string, unknown>;
      return (
        <RequestCard
          key={request.mealRequestId}
          request={request}
          locale={locale}
          translations={{
            id: (tableTranslations.id as string) || '#',
            requester: (tableTranslations.requester as string) || 'Requester',
            title: (tableTranslations.title as string) || 'Title',
            requestTime: (tableTranslations.requestTime as string) || 'Request Time',
            closedTime: (tableTranslations.closedTime as string) || 'Closed Time',
            notes: (tableTranslations.notes as string) || 'Notes',
            mealType: (tableTranslations.mealType as string) || 'Meal Type',
            totalRequests: (tableTranslations.totalRequests as string) || 'Total Requests',
            accepted: (tableTranslations.accepted as string) || 'Accepted',
            status: (tableTranslations.status as string) || 'Status',
            view: (commonTranslations.view as string) || 'View',
            approve: (commonTranslations.approve as string) || 'Approve',
            reject: (commonTranslations.reject as string) || 'Reject',
          }}
          onView={handleView}
          onApprove={handleApprove}
          onReject={handleReject}
          isActionLoading={actionLoadingId === request.mealRequestId}
        />
      );
    },
    [t, locale, handleView, handleApprove, handleReject, actionLoadingId]
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Status Cards */}
      <StatusCards
        stats={stats}
        currentStatus={statusFilter}
        statusOptions={statusOptions}
        onStatusClick={handleStatusChange}
      />

      {/* Table Controller */}
      <RequestsTableController
        fromDate={fromDate}
        toDate={toDate}
        requesterFilter={requesterFilter}
        isLive={isOnline}
        isValidating={isValidating}
        hasActiveFilters={hasActiveFilters}
        onFromDateChange={handleFromDateChange}
        onToDateChange={handleToDateChange}
        onRequesterChange={handleRequesterChange}
      />

      {/* Data Table */}
      <div className="flex flex-col bg-card border rounded-lg shadow-sm">
        <DataTable
          _data={requests}
          columns={columns}
          _isLoading={showLoadingState}
          enableRowSelection={false}
          getRowClassName={getRowClassName}
          renderMobileCard={renderMobileCard}
        />

        {/* Pagination */}
        <Pagination
          totalItems={paginatedData.total}
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
        />
      )}
    </div>
  );
}
