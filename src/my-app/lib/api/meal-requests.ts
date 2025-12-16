/**
 * Client-side API functions for Meal Requests Management
 * Uses fetch to call Next.js API routes (which proxy to backend)
 */

import type { MealRequest, RequestLine, MealRequestStats } from '@/types/meal-request.types';

/**
 * Fetch all meal requests with optional query parameters
 */
export async function getMealRequests(params?: Record<string, string>): Promise<MealRequest[]> {
  try {
    const queryString = params ? new URLSearchParams(params).toString() : '';
    const url = `/api/meal-requests${queryString ? `?${queryString}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      console.error('Failed to fetch meal requests:', response.status);
      return [];
    }

    const result = await response.json();

    // Handle wrapped response format: { ok: true, data: [...] }
    if (result.ok && result.data) {
      return Array.isArray(result.data) ? result.data : [];
    }

    // Handle direct array response
    return Array.isArray(result) ? result : [];
  } catch (error) {
    console.error('Failed to fetch meal requests:', error);
    return [];
  }
}

/**
 * Fetch request lines for a specific meal request
 */
export async function getRequestLines(requestId: number): Promise<RequestLine[]> {
  try {
    const response = await fetch(`/api/request-lines?request_id=${requestId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      console.error('Failed to fetch request lines:', response.status);
      return [];
    }

    const result = await response.json();

    // Handle wrapped response format: { ok: true, data: [...] }
    if (result.ok && result.data) {
      return Array.isArray(result.data) ? result.data : [];
    }

    // Handle direct array response
    return Array.isArray(result) ? result : [];
  } catch (error) {
    console.error('Failed to fetch request lines:', error);
    return [];
  }
}

/**
 * Fetch meal request statistics (counts by status)
 */
export async function getMealRequestStats(): Promise<MealRequestStats> {
  try {
    const response = await fetch('/api/meal-requests/stats', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      console.error('Failed to fetch meal request stats:', response.status);
      return { total: 0, pending: 0, approved: 0, rejected: 0 };
    }

    const result = await response.json();

    // Handle wrapped response format: { ok: true, data: {...} }
    if (result.ok && result.data) {
      return result.data;
    }

    // Handle direct object response
    return result;
  } catch (error) {
    console.error('Failed to fetch meal request stats:', error);
    return { total: 0, pending: 0, approved: 0, rejected: 0 };
  }
}

/**
 * Result type for status update operations
 */
export interface UpdateStatusResult {
  success: boolean;
  error?: string;
  data?: MealRequest;
  isConflict?: boolean;
  currentStatusId?: number;
}

/**
 * Update meal request status (approve or reject)
 * Client-side function that calls Next.js API route
 *
 * @param mealRequestId - The ID of the meal request to update
 * @param statusId - The new status ID (2 = Approved, 3 = Rejected)
 * @param userId - The ID of the user performing the action
 * @param expectedStatusId - Optional: The status ID the client expects. If provided,
 *                           the update will fail with isConflict=true if another user
 *                           has already changed the status.
 */
export async function updateMealRequestStatus(
  mealRequestId: number,
  statusId: number,
  userId: string,
  expectedStatusId?: number
): Promise<UpdateStatusResult> {
  try {
    // Build query string with optional expected_status_id
    const params = new URLSearchParams({
      status_id: statusId.toString(),
      user_id: userId,
    });

    if (expectedStatusId !== undefined) {
      params.append('expected_status_id', expectedStatusId.toString());
    }

    const response = await fetch(
      `/api/meal-requests/${mealRequestId}/status?${params.toString()}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      }
    );

    const result = await response.json();

    // Handle 409 Conflict - status was already changed by another user
    if (response.status === 409) {
      const detail = result.detail || result.error || {};
      return {
        success: false,
        isConflict: true,
        error: typeof detail === 'object' && detail.message
          ? detail.message
          : 'This request has already been updated by another user.',
        currentStatusId: typeof detail === 'object' ? detail.current_status_id : undefined,
      };
    }

    if (!response.ok || !result.ok) {
      return {
        success: false,
        error: result.message || result.error || 'Failed to update request status',
      };
    }

    return {
      success: true,
      data: result.data,
    };
  } catch (error) {
    console.error('Failed to update meal request status:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to update request status',
    };
  }
}
