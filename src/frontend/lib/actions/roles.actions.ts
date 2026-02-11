"use server";

/**
 * Server Actions for Roles Management
 * These functions run on the server and communicate with the backend API
 */

import { serverApi } from "@/lib/http/axios-server";
import type { SettingRolesResponse, RoleResponse } from "@/types/roles";
import type { UserResponse } from "@/types/users";

/**
 * Fetch roles list with pagination and filtering
 */
export async function getRoles(params: {
  limit?: number;
  skip?: number;
  filterCriteria?: {
    is_active?: string;
    role_name?: string;
    role_id?: string;
  };
}): Promise<SettingRolesResponse> {
  try {
    const queryParams: Record<string, string | number> = {
      limit: params.limit ?? 10,
      skip: params.skip ?? 0,
    };

    // Add filters if provided (using snake_case for URL params)
    if (params.filterCriteria?.is_active) {
      queryParams.is_active = params.filterCriteria.is_active;
    }
    if (params.filterCriteria?.role_name) {
      queryParams.role_name = params.filterCriteria.role_name;
    }
    if (params.filterCriteria?.role_id) {
      queryParams.role_id = params.filterCriteria.role_id;
    }

    // Backend returns array directly or wrapped in object
    const result = await serverApi.get<SettingRolesResponse | RoleResponse[]>("/permissions/roles", {
      params: queryParams,
      useVersioning: true, // Requests /api/v1/permissions/roles
    });

    if (result.ok && result.data) {
      // Handle case where backend returns array directly
      if (Array.isArray(result.data)) {
        // Normalize response: camelCase (CamelModel) takes priority, snake_case as fallback
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const roles: RoleResponse[] = (result.data as any[]).map((role: any) => ({
          id: role.id as number,
          nameEn: (role.nameEn ?? role.name_en ?? role.name ?? '') as string,
          nameAr: (role.nameAr ?? role.name_ar ?? '') as string,
          descriptionEn: (role.descriptionEn ?? role.description_en ?? role.description ?? null) as string | null,
          descriptionAr: (role.descriptionAr ?? role.description_ar ?? null) as string | null,
          name: (role.name ?? role.nameEn ?? role.name_en ?? '') as string,
          description: (role.description ?? role.descriptionEn ?? role.description_en ?? null) as string | null,
          isActive: (role.isActive ?? role.is_active ?? true) as boolean,
          createdAt: (role.createdAt ?? role.created_at) as string | undefined,
          updatedAt: (role.updatedAt ?? role.updated_at) as string | undefined,
        }));

        const activeCount = roles.filter(r => r.isActive).length;
        return {
          roles,
          total: roles.length,
          activeCount,
          inactiveCount: roles.length - activeCount,
        };
      }
      // Handle wrapped response
      return result.data as SettingRolesResponse;
    }

    if (!result.ok) {
      console.error("[getRoles] Failed to fetch roles:", result.error);
    }
    // Return empty response on error
    return {
      roles: [],
      total: 0,
      activeCount: 0,
      inactiveCount: 0,
    };
  } catch (error) {
    console.error("Error in getRoles:", error);
    return {
      roles: [],
      total: 0,
      activeCount: 0,
      inactiveCount: 0,
    };
  }
}

/**
 * Fetch a single role by ID
 */
export async function getRoleById(roleId: string): Promise<RoleResponse | null> {
  try {
    const result = await serverApi.get<RoleResponse>(`/auth/roles/${roleId}`, {
      useVersioning: true,
    });

    if (result.ok && result.data) {
      return result.data;
    }

    if (!result.ok) {
      console.error("Failed to fetch role:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getRoleById:", error);
    return null;
  }
}

/**
 * Fetch all users (for role assignment)
 * TODO: Implement pagination if list becomes too large
 */
export async function getAllUsers(): Promise<UserResponse[] | null> {
  try {
    const result = await serverApi.get<{ users: UserResponse[] }>("/auth/users", {
      params: {
        limit: 1000, // Large limit to get all users
        skip: 0,
      },
      useVersioning: true,
    });

    if (result.ok && result.data && result.data.users) {
      return result.data.users;
    }

    if (!result.ok) {
      console.error("Failed to fetch all users:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getAllUsers:", error);
    return null;
  }
}
