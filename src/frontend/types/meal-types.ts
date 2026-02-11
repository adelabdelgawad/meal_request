/**
 * Meal Types Management Types
 * For the meal-type-setup page
 */

export interface MealTypeResponse {
  id: number;
  nameEn: string;
  nameAr: string;
  priority: number;
  isActive: boolean;
  isDeleted: boolean;
  createdAt: string;
  updatedAt: string;
  createdById?: string | null;
  updatedById?: string | null;
}

export interface MealTypeCreate {
  nameEn: string;
  nameAr: string;
  priority?: number;
  createdById?: string | null;
}

export interface MealTypeUpdate {
  nameEn?: string;
  nameAr?: string;
  priority?: number;
  isActive?: boolean;
  updatedById?: string | null;
}

export interface MealTypesResponse {
  items: MealTypeResponse[];
  total: number;
  skip: number;
  limit: number;
  activeCount: number;
  inactiveCount: number;
}
