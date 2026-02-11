'use server';

import { serverApi } from '@/lib/http/axios-server';
import type { MealRequestLine, MealRequest } from '@/types/meal-request.types';

interface CreateMealRequestResponse {
  success: boolean;
  data?: MealRequest;
  error?: string;
}

/**
 * Create a meal request for a specific meal type
 * @param requesterId - UUID of the account creating the request
 * @param mealTypeId - Meal type ID (2 = Lunch, 3 = Dinner)
 * @param requestLines - Array of meal request lines
 */
export async function createMealRequest(
  requesterId: string,
  mealTypeId: number,
  requestLines: MealRequestLine[]
): Promise<CreateMealRequestResponse> {
  try {
    // Convert camelCase to snake_case for backend
    const backendRequestLines = requestLines.map((line) => ({
      employee_id: line.employeeId,
      employee_code: String(line.employeeCode),
      notes: line.notes || '',
    }));

    // Backend expects a direct array, not wrapped in an object
    const response = await serverApi.post(
      `/requests/create-meal-request?requester_id=${requesterId}&meal_type_id=${mealTypeId}`,
      backendRequestLines,
      { useVersioning: true }
    );

    if (!response.ok) {
      const error = 'error' in response ? response.error : 'Failed to create meal request';
      console.error('Failed to create meal request:', error);
      return { success: false, error: String(error) };
    }

    return { success: true, data: response.data as MealRequest };
  } catch (error: unknown) {
    console.error('Failed to create meal request:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'An unexpected error occurred',
    };
  }
}
