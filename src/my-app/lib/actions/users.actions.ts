"use server";

/**
 * Server Actions for Users Management
 * These functions run on the server and communicate with the backend API
 */

import { serverApi } from "@/lib/http/axios-server";
import type {
  SettingUsersResponse,
  UserResponse,
  AuthUserResponse,
} from "@/types/users";

/**
 * Fetch users list with pagination and filtering
 */
export async function getUsers(
  limit: number = 10,
  skip: number = 0,
  filters?: {
    is_active?: string;
    username?: string;
    role?: string;
  }
): Promise<SettingUsersResponse | null> {
  try {
    const params: Record<string, string | number> = {
      limit,
      skip,
    };

    // Add filters if provided (using snake_case for URL params)
    if (filters?.is_active) {
      params.is_active = filters.is_active;
    }
    if (filters?.username) {
      params.username = filters.username;
    }
    if (filters?.role) {
      params.role = filters.role;
    }
    const result = await serverApi.get<SettingUsersResponse>("/auth/users", {
      params,
      useVersioning: true, // Requests /api/v1/auth/users
    });

    if (result.ok && result.data) {
      return result.data;
    }

    if (!result.ok) {
      console.error("Failed to fetch users:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getUsers:", error);
    return null;
  }
}

/**
 * Fetch a single user by ID
 */
export async function getUserById(
  userId: string
): Promise<UserResponse | null> {
  try {
    const result = await serverApi.get<UserResponse>(`/auth/users/${userId}`, {
      useVersioning: true,
    });

    if (result.ok && result.data) {
      return result.data;
    }

    if (!result.ok) {
      console.error("Failed to fetch user:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getUserById:", error);
    return null;
  }
}

interface DomainUserListResponse {
  items: AuthUserResponse[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

/**
 * Fetch domain users from Active Directory cache
 */
export async function getDomainUsers(): Promise<AuthUserResponse[] | null> {
  try {
    const result = await serverApi.get<DomainUserListResponse>(
      "/domain-users",
      {
        params: {
          page: 1,
          limit: 100, // Get first batch
        },
        useVersioning: true,
      }
    );

    if (result.ok && result.data) {
      return result.data.items;
    }

    if (!result.ok) {
      console.error("Failed to fetch domain users:", result.error);
    }
    return null;
  } catch (error) {
    console.error("Error in getDomainUsers:", error);
    return null;
  }
}
