/**
 * Client-side API functions for User Department Assignments
 * These functions manage which departments' meal requests a user can view
 */

import { clientApi } from "@/lib/http/axios-client";

// Response types
export interface UserDepartmentsResponse {
  userId: string;
  departmentIds: number[];
}

export interface DepartmentForAssignment {
  id: number;
  nameEn: string;
  nameAr: string;
  isAssigned: boolean;
}

export interface UserDepartmentsDetailResponse {
  userId: string;
  userName: string | null;
  assignedDepartmentIds: number[];
  departments: DepartmentForAssignment[];
}

// Update request type
export interface UserDepartmentsUpdate {
  departmentIds: number[];
}

/**
 * Get department IDs assigned to a user
 */
export async function getUserDepartments(
  userId: string
): Promise<UserDepartmentsResponse> {
  const result = await clientApi.get<UserDepartmentsResponse>(
    `/setting/users/${userId}/departments`
  );

  if (!result.ok) {
    throw new Error(
      "error" in result ? result.error : "Failed to get user departments"
    );
  }

  return result.data;
}

/**
 * Get detailed department info with assignment status for a user
 * Used for populating the management sheet
 */
export async function getUserDepartmentsDetail(
  userId: string
): Promise<UserDepartmentsDetailResponse> {
  const result = await clientApi.get<UserDepartmentsDetailResponse>(
    `/setting/users/${userId}/departments/detail`
  );

  if (!result.ok) {
    throw new Error(
      "error" in result ? result.error : "Failed to get user departments detail"
    );
  }

  return result.data;
}

/**
 * Update department assignments for a user
 * Empty array = no restrictions (user sees all departments)
 */
export async function updateUserDepartments(
  userId: string,
  departmentIds: number[]
): Promise<UserDepartmentsResponse> {
  const result = await clientApi.put<UserDepartmentsResponse>(
    `/setting/users/${userId}/departments`,
    { departmentIds }
  );

  if (!result.ok) {
    throw new Error(
      "error" in result ? result.error : "Failed to update user departments"
    );
  }

  return result.data;
}

/**
 * Clear all department assignments for a user
 * After this, user can see ALL departments
 */
export async function clearUserDepartments(userId: string): Promise<void> {
  const result = await clientApi.delete(
    `/setting/users/${userId}/departments`
  );

  if (!result.ok) {
    throw new Error(
      "error" in result ? result.error : "Failed to clear user departments"
    );
  }
}
