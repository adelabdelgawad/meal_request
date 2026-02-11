/**
 * Page Types for Settings Pages
 * All field names use camelCase to match backend CamelModel responses
 * Supports bilingual fields (English/Arabic) and navigation metadata
 */

// Page response from backend
export interface PageResponse {
  id: number;
  nameEn: string;
  nameAr: string;
  descriptionEn: string | null;
  descriptionAr: string | null;
  path: string | null;
  icon: string | null; // Lucide-react icon name
  navType: string | null; // Navigation type (primary, sidebar, etc.)
  order: number;
  isMenuGroup: boolean;
  showInNav: boolean;
  openInNewTab: boolean;
  parentId: number | null;
  key: string | null; // Unique key for idempotent seeds
  name: string; // Computed by backend based on user locale
  description: string | null; // Computed by backend based on user locale
}

// Create page request
export interface PageCreateRequest {
  nameEn: string;
  nameAr: string;
  descriptionEn?: string | null;
  descriptionAr?: string | null;
  path?: string | null;
  icon?: string | null;
  navType?: string | null;
  order?: number;
  isMenuGroup?: boolean;
  showInNav?: boolean;
  openInNewTab?: boolean;
  parentId?: number | null;
  key?: string | null;
  // Legacy field for backward compatibility
  name?: string;
}

// Update page request
export interface PageUpdateRequest {
  nameEn?: string;
  nameAr?: string;
  descriptionEn?: string | null;
  descriptionAr?: string | null;
  path?: string | null;
  icon?: string | null;
  navType?: string | null;
  order?: number;
  isMenuGroup?: boolean;
  showInNav?: boolean;
  openInNewTab?: boolean;
  // Legacy field for backward compatibility
  name?: string;
}

// Settings page pages response
export interface SettingPagesResponse {
  pages: PageResponse[];
  total: number;
}

// Simple page for dropdowns
export interface SimplePage {
  id: number;
  name: string;
  path?: string | null;
}
