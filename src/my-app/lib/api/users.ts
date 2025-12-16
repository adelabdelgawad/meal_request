/**
 * Client-side API functions for Users Management
 * These functions call Next.js API routes which proxy to the backend
 */

import { clientApi } from "@/lib/http/axios-client";
import type {
  UserWithRolesResponse,
  UserCreate,
  UserUpdate,
  BulkStatusUpdateResponse,
  UserSourceMetadata,
  UserMarkManualRequest,
  UserStatusOverrideRequest,
  UserStatusOverrideResponse,
} from "@/types/users";

/**
 * Toggle user active/inactive status
 */
export async function toggleUserStatus(
  userId: string,
  isActive: boolean
): Promise<UserWithRolesResponse> {
  const result = await clientApi.put<UserWithRolesResponse>(
    `/auth/users/${userId}/status`,
    {
      userId, // camelCase in request body
      isActive, // camelCase in request body
    }
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to toggle user status");
  }

  return result.data;
}

/**
 * Toggle user blocked status
 */
export async function toggleUserBlock(
  userId: string,
  isBlocked: boolean
): Promise<UserWithRolesResponse> {
  const result = await clientApi.patch<UserWithRolesResponse>(
    `/auth/users/${userId}/block`,
    {
      isBlocked, // camelCase in request body
    }
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to toggle user block status");
  }

  return result.data;
}

/**
 * Update user information
 */
export async function updateUser(
  userId: string,
  data: UserUpdate
): Promise<UserWithRolesResponse> {
  const result = await clientApi.put<UserWithRolesResponse>(
    `/auth/users/${userId}`,
    data // Already in camelCase
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to update user");
  }

  return result.data;
}

/**
 * Create a new user
 */
export async function createUser(data: UserCreate): Promise<UserWithRolesResponse> {
  const result = await clientApi.post<UserWithRolesResponse>(
    `/auth/users`,
    data // Already in camelCase
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to create user");
  }

  return result.data;
}

/**
 * Delete a user
 */
export async function deleteUser(userId: string): Promise<void> {
  const result = await clientApi.delete(`/auth/users/${userId}`);

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to delete user");
  }
}

/**
 * Bulk update user status
 */
export async function bulkUpdateUserStatus(
  userIds: string[],
  isActive: boolean
): Promise<BulkStatusUpdateResponse> {
  const result = await clientApi.put<BulkStatusUpdateResponse>(
    `/auth/users/status`,
    {
      userIds, // camelCase in request body
      isActive, // camelCase in request body
    }
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to bulk update user status");
  }

  return result.data;
}

/**
 * Update user roles
 * Returns the updated user with new roles from backend
 */
export async function updateUserRoles(
  userId: string,
  roleIds: number[]
): Promise<UserWithRolesResponse> {
  const result = await clientApi.put<UserWithRolesResponse>(
    `/auth/users/${userId}/roles`,
    { roleIds }
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to update user roles");
  }

  return result.data;
}

/**
 * Alias for bulkUpdateUserStatus (used in table actions)
 */
export async function updateUsersStatus(
  userIds: string[],
  isActive: boolean
): Promise<BulkStatusUpdateResponse> {
  return bulkUpdateUserStatus(userIds, isActive);
}

// ============================================================================
// Strategy A: User Source and Override Management API Functions
// ============================================================================

/**
 * Get available user source types with localized metadata
 * No authentication required (public metadata)
 */
export async function getUserSources(): Promise<UserSourceMetadata[]> {
  const result = await clientApi.get<UserSourceMetadata[]>('/admin/user-sources');

  if (!result.ok) {
    throw new Error('error' in result ? result.error : 'Failed to fetch user sources');
  }

  return result.data;
}

/**
 * Mark a user as manual (non-HRIS)
 * Changes user_source to 'manual' so HRIS sync will skip this user
 * Requires Super Admin role
 */
export async function markUserAsManual(
  userId: string,
  data: UserMarkManualRequest
): Promise<UserWithRolesResponse> {
  const result = await clientApi.post<UserWithRolesResponse>(
    `/admin/users/${userId}/mark-manual`,
    data
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : 'Failed to mark user as manual');
  }

  return result.data;
}

/**
 * Enable or disable status override for a user
 * When enabled, HRIS sync will not modify this user's is_active status
 * Requires Super Admin role
 */
export async function overrideUserStatus(
  userId: string,
  data: UserStatusOverrideRequest
): Promise<UserStatusOverrideResponse> {
  const result = await clientApi.post<UserStatusOverrideResponse>(
    `/admin/users/${userId}/override-status`,
    data
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : 'Failed to update status override');
  }

  return result.data;
}
