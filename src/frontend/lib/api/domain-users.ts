/**
 * Client-side API functions for Domain Users
 * These functions call Next.js API routes which proxy to the backend
 */

import { clientApi } from "@/lib/http/axios-client";
import type {
  DomainUser,
  DomainUserListResponse,
  DomainUserQueryParams,
} from "@/types/domain-users";

/**
 * Fetch domain users with pagination and search
 *
 * @param params - Query parameters (q, page, limit)
 * @returns Promise with paginated domain users
 */
export async function fetchDomainUsers(
  params: DomainUserQueryParams = {}
): Promise<DomainUserListResponse> {
  const queryParams: Record<string, string> = {};

  if (params.q) {
    queryParams.q = params.q;
  }
  if (params.page !== undefined) {
    queryParams.page = params.page.toString();
  }
  if (params.limit !== undefined) {
    queryParams.limit = params.limit.toString();
  }

  const result = await clientApi.get<DomainUserListResponse>("/domain-users", {
    params: queryParams,
  });

  if (!result.ok) {
    throw new Error("error" in result ? result.error : "Failed to fetch domain users");
  }

  return result.data;
}

/**
 * Get a single domain user by ID
 *
 * @param id - Domain user ID
 * @returns Promise with domain user
 */
export async function getDomainUser(id: number): Promise<DomainUser> {
  const result = await clientApi.get<DomainUser>(`/domain-users/${id}`);

  if (!result.ok) {
    throw new Error("error" in result ? result.error : "Failed to fetch domain user");
  }

  return result.data;
}
