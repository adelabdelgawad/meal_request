/**
 * Server Actions for Meal Types Management
 */

"use server";

import { serverApi } from "@/lib/http/axios-server";
import type {
  MealTypesResponse,
  MealTypeResponse,
  MealTypeCreate,
  MealTypeUpdate,
} from "@/types/meal-types";

interface GetMealTypesParams {
  limit?: number;
  skip?: number;
  filterCriteria?: {
    active_only?: string;
  };
}

/**
 * Get paginated meal types with filtering
 */
export async function getMealTypes(
  params: GetMealTypesParams = {}
): Promise<MealTypesResponse> {
  const { limit = 10, skip = 0, filterCriteria = {} } = params;

  const queryParams: Record<string, string> = {
    limit: limit.toString(),
    skip: skip.toString(),
  };

  if (filterCriteria.active_only !== undefined) {
    queryParams.active_only = filterCriteria.active_only;
  }

  try {
    const result = await serverApi.get<MealTypesResponse>("/meal-types/paginated", {
      params: queryParams,
      useVersioning: true,
    });

    if (!result.ok) {
      console.error("Failed to fetch meal types:", result.error);
      return {
        items: [],
        total: 0,
        skip,
        limit,
        activeCount: 0,
        inactiveCount: 0,
      };
    }

    return result.data;
  } catch (error) {
    console.error("Error fetching meal types:", error);
    return {
      items: [],
      total: 0,
      skip,
      limit,
      activeCount: 0,
      inactiveCount: 0,
    };
  }
}

/**
 * Get a specific meal type by ID
 */
export async function getMealType(id: number): Promise<MealTypeResponse | null> {
  try {
    const result = await serverApi.get<MealTypeResponse>(`/meal-types/${id}`, {
      useVersioning: true,
    });

    if (!result.ok) {
      console.error("Failed to fetch meal type:", result.error);
      return null;
    }

    return result.data;
  } catch (error) {
    console.error("Error fetching meal type:", error);
    return null;
  }
}

/**
 * Create a new meal type
 */
export async function createMealType(
  data: MealTypeCreate
): Promise<{ success: boolean; data?: MealTypeResponse; error?: string }> {
  try {
    const result = await serverApi.post<MealTypeResponse>("/meal-types", data, {
      useVersioning: true,
    });

    if (!result.ok) {
      return {
        success: false,
        error: result.error || "Failed to create meal type",
      };
    }

    return {
      success: true,
      data: result.data,
    };
  } catch (error) {
    console.error("Error creating meal type:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

/**
 * Update an existing meal type
 */
export async function updateMealType(
  id: number,
  data: MealTypeUpdate
): Promise<{ success: boolean; data?: MealTypeResponse; error?: string }> {
  try {
    const result = await serverApi.put<MealTypeResponse>(`/meal-types/${id}`, data, {
      useVersioning: true,
    });

    if (!result.ok) {
      return {
        success: false,
        error: result.error || "Failed to update meal type",
      };
    }

    return {
      success: true,
      data: result.data,
    };
  } catch (error) {
    console.error("Error updating meal type:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

/**
 * Delete a meal type (soft delete)
 */
export async function deleteMealType(
  id: number
): Promise<{ success: boolean; error?: string }> {
  try {
    const result = await serverApi.delete(`/meal-types/${id}`, {
      useVersioning: true,
    });

    if (!result.ok) {
      return {
        success: false,
        error: result.error || "Failed to delete meal type",
      };
    }

    return {
      success: true,
    };
  } catch (error) {
    console.error("Error deleting meal type:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}
