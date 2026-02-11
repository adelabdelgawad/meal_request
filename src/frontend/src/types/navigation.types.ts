/**
 * Navigation Types
 * All types use camelCase to match backend responses
 */

export interface NavigationNode {
  id: number;
  key: string | null;
  name: string;
  nameEn: string;
  nameAr: string;
  description: string | null;
  descriptionEn: string | null;
  descriptionAr: string | null;
  navType: string | null;
  isMenuGroup: boolean;
  showInNav: boolean;
  openInNewTab: boolean;
  parentId: number | null;
  children: NavigationNode[];
}

export interface NavigationResponse {
  items: NavigationNode[];
}
