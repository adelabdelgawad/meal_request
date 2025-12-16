/**
 * User Types for Settings Pages
 * These types are isolated from auth types to avoid breaking login/session logic
 * All field names use camelCase to match backend CamelModel responses
 */

// User Source Metadata - Localized metadata for user source types
export interface UserSourceMetadata {
  code: string; // Technical identifier (hris/manual)
  nameEn: string; // English display name
  nameAr: string; // Arabic display name
  descriptionEn: string; // English description for tooltips
  descriptionAr: string; // Arabic description for tooltips
  icon: string; // Icon identifier for UI (e.g., 'database', 'user-edit')
  color: string; // Color code for badges (e.g., 'blue', 'green')
  canOverride: boolean; // Whether users of this source can have status overrides
}

// Base user response from backend
export interface UserResponse {
  id: string; // UUID
  username: string;
  email: string | null;
  fullName: string | null;
  title: string | null;
  isActive: boolean;
  isBlocked: boolean;
  isDomainUser: boolean;
  isSuperAdmin: boolean;
  roleId: number | null;
  createdAt: string;
  updatedAt: string;
  // Strategy A: Source Tracking and Status Override Fields
  userSource: string; // Source of user record: 'hris' or 'manual'
  userSourceMetadata?: UserSourceMetadata | null; // Localized metadata for user source
  statusOverride: boolean; // If true, is_active status is manually controlled (HRIS sync skips)
  overrideReason?: string | null; // Admin-provided reason for status override
  overrideSetById?: string | null; // User ID of admin who set the override
  overrideSetAt?: string | null; // Timestamp when override was enabled
}

// User with role information for table display
export interface UserWithRolesResponse extends UserResponse {
  roles: string[]; // Role names array for multi-role display
  roleIds: number[]; // Role IDs array for matching with dropdown options
  assignedDepartmentCount?: number; // Number of assigned departments (null/0 = ALL)
}

// Create user request
export interface UserCreate {
  username: string;
  email?: string | null;
  fullName?: string | null;
  title?: string | null;
  isActive?: boolean;
  isDomainUser?: boolean;
  isSuperAdmin?: boolean;
  roleId?: number | null;
  password?: string; // Required for local users, optional for domain users
}

// Update user request
export interface UserUpdate {
  email?: string | null;
  fullName?: string | null;
  title?: string | null;
  isActive?: boolean;
  roleId?: number | null;
}

// Block user request
export interface UserBlockUpdate {
  isBlocked: boolean;
}

// Settings page users response with pagination and counts
export interface SettingUsersResponse {
  users: UserWithRolesResponse[];
  total: number;
  activeCount: number;
  inactiveCount: number;
  roleOptions: SimpleRole[]; // Available roles for filtering
}

// Simple role for dropdowns and filters
export interface SimpleRole {
  id: number; // Integer ID
  name: string;
  nameEn?: string;
  nameAr?: string;
  totalUsers?: number; // Count of users with this role
}

// Domain user (from Active Directory cache)
export interface AuthUserResponse {
  id: number;
  username: string;
  email?: string | null;
  fullName?: string | null;
  title?: string | null;
  office?: string | null;
  phone?: string | null;
  manager?: string | null;
  createdAt?: string;
  updatedAt?: string;
}

// Bulk status update request
export interface BulkStatusUpdateRequest {
  userIds: string[];
  isActive: boolean;
}

// Bulk status update response
export interface BulkStatusUpdateResponse {
  updatedUsers: UserWithRolesResponse[];
}

// Re-export RoleResponse for components that import it from this module
export type { RoleResponse } from './roles';

// Strategy A: User Source and Override Management Types

// Request to mark a user as manual (non-HRIS)
export interface UserMarkManualRequest {
  reason: string; // Reason for marking user as manual (min 20 characters)
}

// Request to enable/disable status override for a user
export interface UserStatusOverrideRequest {
  statusOverride: boolean; // Whether to enable (true) or disable (false) status override
  overrideReason?: string | null; // Reason for override (required when enabling, min 20 characters)
}

// Response from status override operation
export interface UserStatusOverrideResponse {
  user: UserWithRolesResponse; // Updated user object
  message: string; // Success message
}
