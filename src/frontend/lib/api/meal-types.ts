/**
 * Server-side API functions for Meal Types
 * Used in server components to fetch meal type data
 */

import { serverApi } from '@/lib/http/axios-server';
import type { MealType } from '@/types/meal-request.types';

/**
 * Fetch all active meal types
 */
export async function getActiveMealTypes(): Promise<MealType[]> {
  try {
    const response = await serverApi.get<MealType[]>('/meal-types', {
      useVersioning: true,
      params: { activeOnly: true },
    });

    if (!response.ok) {
      console.error('Failed to fetch meal types:', response);
      return [];
    }

    return response.data || [];
  } catch (error) {
    console.error('Failed to fetch meal types:', error);
    return [];
  }
}

/**
 * Fetch all meal types (including inactive)
 */
export async function getAllMealTypes(): Promise<MealType[]> {
  try {
    const response = await serverApi.get<MealType[]>('/meal-types', {
      useVersioning: true,
      params: { activeOnly: false },
    });

    if (!response.ok) {
      console.error('Failed to fetch meal types:', response);
      return [];
    }

    return response.data || [];
  } catch (error) {
    console.error('Failed to fetch meal types:', error);
    return [];
  }
}

/**
 * Fetch a single meal type by ID
 */
export async function getMealTypeById(id: number): Promise<MealType | null> {
  try {
    const response = await serverApi.get<MealType>(`/meal-types/${id}`, {
      useVersioning: true,
    });

    if (!response.ok) {
      console.error(`Failed to fetch meal type ${id}:`, response);
      return null;
    }

    return response.data || null;
  } catch (error) {
    console.error(`Failed to fetch meal type ${id}:`, error);
    return null;
  }
}
