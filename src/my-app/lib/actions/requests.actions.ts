'use server';

import { serverApi } from '@/lib/http/axios-server';
import type { UpdateRequestLinePayload, PaginatedMealRequests, MealRequestStats, CopyMealRequestResponse, RequestLine } from '@/types/meal-request.types';

/**
 * Update meal request status (approve or reject)
 * @param mealRequestId - ID of the meal request
 * @param statusId - Status ID (2 = Approved, 3 = Rejected)
 * @param userId - ID of the user performing the action
 */
export async function updateMealRequestStatus(
  mealRequestId: number,
  statusId: number,
  userId: string
) {
  try {
    const response = await serverApi.put(
      `/requests/${mealRequestId}/status`,
      {},
      {
        params: {
          status_id: statusId,
          user_id: userId,
        },
        useVersioning: true,
      }
    );

    if (!response.ok) {
      return {
        success: false,
        error: 'error' in response ? response.error : 'Failed to update request status',
      };
    }

    return { success: true, data: response.data };
  } catch (error: unknown) {
    console.error('Failed to update meal request status:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to update request status',
    };
  }
}

/**
 * Update a request line (acceptance status and notes)
 */
export async function updateRequestLine(payload: UpdateRequestLinePayload) {
  try {
    const response = await serverApi.put(
      `/requests/lines/${payload.mealRequestLineId}`,
      {
        userId: payload.userId,
        mealRequestLineId: payload.mealRequestLineId,
        accepted: payload.accepted,
        notes: payload.notes || '',
      },
      { useVersioning: true }
    );

    if (!response.ok) {
      return {
        success: false,
        error: 'error' in response ? response.error : 'Failed to update request line',
      };
    }

    return { success: true, data: response.data };
  } catch (error: unknown) {
    console.error('Failed to update request line:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to update request line',
    };
  }
}

// Default empty stats for fallback
const EMPTY_STATS: MealRequestStats = { total: 0, pending: 0, approved: 0, rejected: 0 };

/**
 * Server action to fetch meal requests with filtering and pagination
 * Used for SSR data loading
 *
 * Returns a unified response with items, pagination metadata, and stats.
 * Stats are computed using the same filters (requester, date range) but exclude
 * status filter to show counts across all statuses for the filtered dataset.
 */
export async function getMealRequests(filters?: {
  status?: string; // Status ID as string
  requester?: string;
  from_date?: string;
  to_date?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedMealRequests> {
  try {
    const params: Record<string, string> = {};

    if (filters?.status && filters.status !== 'all') {
      // Use status_id for filtering (status is already an ID string from URL)
      params.status_id = filters.status;
    }
    if (filters?.requester) {
      params.requester = filters.requester;
    }
    if (filters?.from_date) {
      params.from_date = filters.from_date;
    }
    if (filters?.to_date) {
      params.to_date = filters.to_date;
    }
    if (filters?.page) {
      params.page = filters.page.toString();
    }
    if (filters?.page_size) {
      params.page_size = filters.page_size.toString();
    }

    const response = await serverApi.get('/requests/all', {
      params,
      useVersioning: true,
    });

    if (!response.ok) {
      console.error('Failed to fetch meal requests:', response.error);
      return { items: [], total: 0, page: 1, page_size: 50, total_pages: 0, stats: EMPTY_STATS };
    }

    // Handle paginated response with stats
    if (response.data && typeof response.data === 'object' && 'items' in response.data) {
      const data = response.data as PaginatedMealRequests;
      return {
        ...data,
        stats: data.stats || EMPTY_STATS,
      };
    }

    // Handle legacy array response (backward compatibility)
    if (Array.isArray(response.data)) {
      return {
        items: response.data,
        total: response.data.length,
        page: 1,
        page_size: response.data.length,
        total_pages: 1,
        stats: EMPTY_STATS,
      };
    }

    return { items: [], total: 0, page: 1, page_size: 50, total_pages: 0, stats: EMPTY_STATS };
  } catch (error: unknown) {
    console.error('Failed to fetch meal requests:', error);
    return { items: [], total: 0, page: 1, page_size: 50, total_pages: 0, stats: EMPTY_STATS };
  }
}

/**
 * Server action to fetch meal request statistics
 * Used for SSR data loading
 */
export async function getMealRequestStats(): Promise<MealRequestStats> {
  try {
    const response = await serverApi.get('/requests/stats', {
      useVersioning: true,
    });

    if (!response.ok) {
      console.error('Failed to fetch meal request stats:', response.error);
      return { total: 0, pending: 0, approved: 0, rejected: 0 };
    }

    return response.data as MealRequestStats;
  } catch (error: unknown) {
    console.error('Failed to fetch meal request stats:', error);
    return { total: 0, pending: 0, approved: 0, rejected: 0 };
  }
}

/**
 * Fetch meal request status options
 * @param activeOnly - Whether to fetch only active statuses (default: true)
 */
export async function getMealRequestStatusOptions(activeOnly: boolean = true): Promise<Array<{
  id: number;
  nameEn: string;
  nameAr: string;
  isActive: boolean;
}>> {
  try {
    const response = await serverApi.get('/requests/status-options', {
      params: {
        active_only: activeOnly,
      },
      useVersioning: true,
    });

    if (!response.ok) {
      console.error('Failed to fetch status options:', response.error);
      return [];
    }

    // Convert snake_case to camelCase
    const data = response.data as Array<{
      id: number;
      name_en: string;
      name_ar: string;
      is_active: boolean;
    }>;

    return data.map(item => ({
      id: item.id,
      nameEn: item.name_en,
      nameAr: item.name_ar,
      isActive: item.is_active,
    }));
  } catch (error: unknown) {
    console.error('Failed to fetch status options:', error);
    return [];
  }
}

/**
 * Server action to fetch current user's own meal requests
 * Used for SSR data loading on the history-requests page
 *
 * Returns a unified response with items, pagination metadata, and stats.
 * This endpoint automatically filters by the current user's ID from the JWT token.
 */
export async function getMyMealRequests(filters?: {
  status?: string; // Status ID as string
  from_date?: string;
  to_date?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedMealRequests> {
  try {
    const params: Record<string, string> = {};

    if (filters?.status && filters.status !== 'all') {
      params.status_id = filters.status;
    }
    if (filters?.from_date) {
      params.from_date = filters.from_date;
    }
    if (filters?.to_date) {
      params.to_date = filters.to_date;
    }
    if (filters?.page) {
      params.page = filters.page.toString();
    }
    if (filters?.page_size) {
      params.page_size = filters.page_size.toString();
    }

    const response = await serverApi.get('/requests/my', {
      params,
      useVersioning: true,
    });

    if (!response.ok) {
      console.error('Failed to fetch my meal requests:', response.error);
      return { items: [], total: 0, page: 1, page_size: 50, total_pages: 0, stats: EMPTY_STATS };
    }

    // Handle paginated response with stats
    if (response.data && typeof response.data === 'object' && 'items' in response.data) {
      const data = response.data as PaginatedMealRequests;
      return {
        ...data,
        stats: data.stats || EMPTY_STATS,
      };
    }

    // Handle legacy array response (backward compatibility)
    if (Array.isArray(response.data)) {
      return {
        items: response.data,
        total: response.data.length,
        page: 1,
        page_size: response.data.length,
        total_pages: 1,
        stats: EMPTY_STATS,
      };
    }

    return { items: [], total: 0, page: 1, page_size: 50, total_pages: 0, stats: EMPTY_STATS };
  } catch (error: unknown) {
    console.error('Failed to fetch my meal requests:', error);
    return { items: [], total: 0, page: 1, page_size: 50, total_pages: 0, stats: EMPTY_STATS };
  }
}

/**
 * Server action to copy an existing meal request
 * Creates a new request with the same lines but fresh IDs and default values
 * @param requestId - ID of the meal request to copy
 */
export async function copyMealRequest(
  requestId: number
): Promise<{ success: boolean; data?: CopyMealRequestResponse; error?: string }> {
  try {
    const response = await serverApi.post<CopyMealRequestResponse>(
      `/requests/${requestId}/copy`,
      {},
      { useVersioning: true }
    );

    if (!response.ok) {
      return {
        success: false,
        error: 'error' in response ? response.error : 'Failed to copy request',
      };
    }

    return { success: true, data: response.data as CopyMealRequestResponse };
  } catch (error: unknown) {
    console.error('Failed to copy meal request:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to copy request',
    };
  }
}

/**
 * Server action to fetch request lines for a specific meal request
 * Used for prefetching before opening the detail modal
 * @param requestId - ID of the meal request
 * @returns Array of request lines or empty array on error
 */
export async function getRequestLines(requestId: number): Promise<RequestLine[]> {
  try {
    const response = await serverApi.get('/requests/lines', {
      params: { request_id: requestId },
      useVersioning: true,
    });

    if (!response.ok) {
      console.error('Failed to fetch request lines:', response.error);
      return [];
    }

    return Array.isArray(response.data) ? response.data : [];
  } catch (error: unknown) {
    console.error('Error fetching request lines:', error);
    return [];
  }
}
