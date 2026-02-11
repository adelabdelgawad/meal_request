/**
 * Domain User Types
 *
 * Types for Active Directory domain users cached in the database.
 * Used for user selection dropdowns and domain user management.
 */

/**
 * Domain user response from the API
 */
export interface DomainUser {
  id: number;
  username: string;
  email: string | null;
  fullName: string | null;
  title: string | null;
  office: string | null;
  phone: string | null;
  manager: string | null;
  createdAt?: string;
  updatedAt?: string;
}

/**
 * Paginated domain users list response
 */
export interface DomainUserListResponse {
  items: DomainUser[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

/**
 * Query parameters for fetching domain users
 */
export interface DomainUserQueryParams {
  q?: string;
  page?: number;
  limit?: number;
}
