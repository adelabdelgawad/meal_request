/**
 * Role Types for Settings Pages
 * All field names use camelCase to match backend CamelModel responses
 * Supports bilingual fields (English/Arabic)
 */

// Base role response from backend
export interface RoleResponse {
  id: number; // Integer ID
  nameEn: string;
  nameAr: string;
  descriptionEn: string | null;
  descriptionAr: string | null;
  name: string; // Computed by backend based on user locale
  description: string | null; // Computed by backend based on user locale
  createdAt?: string;
  updatedAt?: string;

  // Extended fields (may be included in list responses)
  isActive?: boolean;
  totalUsers?: number;
  pagesNameEn?: string[];
  pagesNameAr?: string[];
}

// Create role request
export interface RoleCreateRequest {
  nameEn: string;
  nameAr: string;
  descriptionEn?: string | null;
  descriptionAr?: string | null;
  // Legacy fields for backward compatibility
  name?: string; // Maps to nameEn
  description?: string | null; // Maps to descriptionEn
}

// Update role request
export interface RoleUpdateRequest {
  nameEn?: string;
  nameAr?: string;
  descriptionEn?: string | null;
  descriptionAr?: string | null;
  // Legacy fields for backward compatibility
  name?: string;
  description?: string | null;
}

// Role form values (for react-hook-form)
export interface RoleValues {
  nameEn: string;
  nameAr: string;
  descriptionEn?: string;
  descriptionAr?: string;
}

// Settings page roles response with pagination and counts
export interface SettingRolesResponse {
  roles: RoleResponse[];
  total: number;
  activeCount: number;
  inactiveCount: number;
}

// Role assignment to pages
export interface RolePageAssignment {
  roleId: number;
  pageIds: number[];
}

// Role assignment to users
export interface RoleUserAssignment {
  roleId: number;
  userIds: string[];
}

// Simple role for dropdowns (used in other modules)
export interface SimpleRole {
  id: number; // Integer ID
  name: string;
}

// Extended role response with related entities
export interface RoleWithRelationsResponse extends RoleResponse {
  users?: { id: string; username: string }[];
  pages?: { id: number; name: string }[];
  userCount?: number;
  pageCount?: number;
}

// Role user info (minimal user info in role context)
export interface RoleUserInfo {
  id: string;
  username: string;
  fullName: string | null;
}

// Role users response from backend
export interface RoleUsersResponse {
  roleId: number;
  users: RoleUserInfo[];
  total: number;
}
