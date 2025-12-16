/**
 * Client-side API functions for Roles Management
 * These functions call Next.js API routes which proxy to the backend
 */

import { clientApi } from "@/lib/http/axios-client";
import type {
  RoleResponse,
  RoleCreateRequest,
  RoleUpdateRequest,
  RoleUserInfo,
  RoleUsersResponse,
} from "@/types/roles";
import type { PageResponse } from "@/types/pages";

/**
 * Create a new role
 */
export async function createRole(data: RoleCreateRequest): Promise<RoleResponse> {
  const result = await clientApi.post<RoleResponse>(
    `/auth/roles`,
    data // Already in camelCase
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to create role");
  }

  return result.data;
}

/**
 * Update role information
 */
export async function updateRole(
  roleId: number,
  data: RoleUpdateRequest
): Promise<RoleResponse> {
  const result = await clientApi.put<RoleResponse>(
    `/auth/roles/${roleId}`,
    data // Already in camelCase
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to update role");
  }

  return result.data;
}

/**
 * Delete a role
 */
export async function deleteRole(roleId: number): Promise<void> {
  const result = await clientApi.delete(`/auth/roles/${roleId}`);

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to delete role");
  }
}

/**
 * Toggle role active/inactive status
 */
export async function toggleRoleStatus(
  roleId: number,
  isActive: boolean
): Promise<RoleResponse> {
  const result = await clientApi.put<RoleResponse>(
    `/auth/roles/${roleId}/status`,
    { isActive } // Only send isActive, roleId is in the URL
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to toggle role status");
  }

  return result.data;
}

/**
 * Fetch users assigned to a role
 */
export async function fetchRoleUsers(
  roleId: number,
  includeInactive?: boolean
): Promise<RoleUserInfo[]> {
  const params = new URLSearchParams();
  if (includeInactive !== undefined) {
    params.append("includeInactive", String(includeInactive));
  }

  const url = `/auth/roles/${roleId}/users${params.toString() ? `?${params.toString()}` : ""}`;
  const result = await clientApi.get<RoleUsersResponse>(url);

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to fetch role users");
  }

  return result.data.users; // Extract users array from response object
}

/**
 * Get pages assigned to a role
 */
export async function getRolePages(
  roleId: number,
  includeInactive?: boolean
): Promise<PageResponse[]> {
  const params = new URLSearchParams();
  if (includeInactive !== undefined) {
    params.append("includeInactive", String(includeInactive));
  }

  const url = `/auth/roles/${roleId}/pages${params.toString() ? `?${params.toString()}` : ""}`;
  const result = await clientApi.get<{ roleId: string; pages: PageResponse[]; total: number }>(url);

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to fetch role pages");
  }

  return result.data.pages; // Extract pages array from response object
}

/**
 * Update pages assigned to a role
 */
export async function updateRolePages(
  roleId: number,
  pageIds: number[]
): Promise<void> {
  const result = await clientApi.put(
    `/auth/roles/${roleId}/pages`,
    { pageIds }
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to update role pages");
  }
}

/**
 * Update users assigned to a role
 */
export async function updateRoleUsers(
  roleId: number,
  userIds: string[]
): Promise<void> {
  const result = await clientApi.put(
    `/auth/roles/${roleId}/users`,
    { userIds }
  );

  if (!result.ok) {
    throw new Error('error' in result ? result.error : "Failed to update role users");
  }
}
